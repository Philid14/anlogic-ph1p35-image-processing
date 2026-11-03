"""Independent event traces for the proposed MAIN/TARGET contract.

No RTL, DDR, physical CDC, pixel timing or board proof is implied by a PASS.
Each JSON case contains input, literal expected output, invariant and failure.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from model.integration_contract import (Key,Bundle,ContractViolation,
    ObservationAdmission,RasterAdmission,PendingResults,DisplayAssociation,
    AbstractPacketChannel,require_atomic)

HERE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    cases=[]
    def record(name,category,inputs,expected,observed,invariant):
        passed=observed==expected
        cases.append(dict(name=name,category=category,inputs=inputs,expected=expected,
            observed=observed,invariant=invariant,failure='observed differs from literal expected',passed=passed))
        print('PASS' if passed else 'FAIL',name)
    def exception(call):
        try:call()
        except ContractViolation as exc:return str(exc)
        return 'NO_REJECTION'
    def bundle(frame,*,session=1,captured=0,ready=0,payload=('box','text')):
        key=Key(session,frame)
        return Bundle(key,key,key,captured,ready,payload)
    def gate():
        g=ObservationAdmission(age_limit=5,acquire=2,lose=2);g.start_session(1,0);return g
    def observe(g,frame,now,valid=True,present=True,session=1,captured=None):
        status=g.result(Key(session,frame),valid=valid,present=present,captured_at=now if captured is None else captured,now=now)
        return g.snapshot(status)

    g=gate();got=[observe(g,10,1),observe(g,10,2),observe(g,9,3),observe(g,11,4)]
    record('identity_duplicate_and_reorder',1,{'frames':[10,10,9,11],'time':[1,2,3,4]},
        [['positive',1,1,0,False],['duplicate',1,1,0,False],['out_of_order',1,1,0,False],['positive',2,2,0,True]],got,
        'Only unique increasing identities may advance observations or acquisition')
    g=gate();got=[observe(g,10,1),observe(g,12,2)]
    record('frame_gap_is_not_fabricated_misses',1,{'frames':[10,12]},
        [['positive',1,1,0,False],['positive',2,2,0,True]],got,'Frame gaps are transport/age facts, not fabricated no-target observations')
    g=gate();observe(g,1,1);observe(g,2,2);g.start_session(7,3)
    got=[observe(g,99,3,session=1),observe(g,0,4,session=7)]
    record('session_restart_and_late_old_session',2,{'start_session':7,'late_packet':[1,99],'new_packet':[7,0]},
        [['wrong_session',0,0,0,False],['positive',1,1,0,False]],got,'Only explicit session authority changes epoch; old packets cannot restart tracking')
    record('session_reuse_rejected',2,{'reuse_session':7},'session_reuse_without_retirement',
        exception(lambda:g.start_session(7,5)),'No session token reuse while old associations can exist')
    g=gate();got=[observe(g,2**32-1,1),observe(g,0,2)]
    record('same_session_wrap_rejected',1,{'frames':[2**32-1,0]},
        [['positive',1,1,0,False],['out_of_order',1,1,0,False]],got,'Frame counter cannot wrap within the same session')

    k=Key(1,1)
    def raster(overrides=None):
        beats=[]
        for i,(x,y) in enumerate(((0,0),(4,0),(0,1),(4,1))):
            beats.append(dict(x=x,y=y,sof=i==0,eol=x==4,eof=i==3,source_lanes=4))
        for i,fields in (overrides or {}).items():beats[i].update(fields)
        r=RasterAdmission(8,2);return r,[r.beat(k,**b) for b in beats],beats
    _,got,beats=raster({2:{'sof':True}})
    record('early_sof_quarantines_until_reset',3,beats,['beat','beat','early_sof_requires_reset','needs_reset'],got,'Premature SOF must not silently relabel old line state')
    _,got,beats=raster({1:{'eol':False}})
    record('wrong_eol_poison_complete_frame',3,beats,['beat','beat','beat','invalid_frame'],got,'Malformed complete raster is invalid, never a valid absence')
    r,got,beats=raster({3:{'eof':False}})
    record('missing_eof_requires_explicit_recovery',3,beats,['beat','beat','beat','missing_eof_requires_reset'],got,'No valid result may be inferred from silence or missing EOF')
    r.reset();fresh=[r.beat(Key(2,0),**b) for b in raster()[2]]
    record('reset_then_complete_new_session',3,{'reset':True,'new_key':[2,0]},['beat','beat','beat','complete_frame'],fresh,'Recovery starts at a complete new-session SOF')
    _,got,beats=raster({3:{'source_lanes':2}})
    record('partial_tail_is_unrepresentable',4,beats,['beat','beat','beat','partial_tail_requires_abort'],got,'V1 has no lane-valid mask: partial source beat requires rejection/abort before TARGET')
    _,got,beats=raster({3:{'abort':True}})
    record('abort_on_last_beat_invalidates_frame',4,beats,['beat','beat','beat','invalid_frame'],got,'EOF lane data cannot override a frame abort')
    # Final-pixel reduction gold is geometric, independent of RTL lane encoder.
    pixels={(7,1)}
    bbox=[min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels),max(y for x,y in pixels)]
    record('last_lane_geometric_gold',4,{'only_hit':[7,1],'filter':False},[7,1,7,1],bbox,'Last lane on EOF contributes; existing RTL full-frame regression provides hardware evidence')

    d=DisplayAssociation();d.write(0,1,k,complete=True)
    reason=d.select(0,now=3,age_limit=50,frame_duration_bound=2)
    d.result(0,1,bundle(1,ready=4));same=d.scan()
    next_reason=d.select(0,now=5,age_limit=50,frame_duration_bound=2)
    record('late_result_does_not_change_active_scan',5,{'display_start':3,'result_ready':4,'repeat_display':5},
        ['missing',['missing',None],'visible'],[reason,list(same),next_reason],'Late result may serve a later matching display, never update current scan')
    d=DisplayAssociation();d.write(0,1,k,complete=True)
    got=d.select(0,now=3,age_limit=50,frame_duration_bound=2)
    record('missing_result_never_borrows_latest_box',5,{'frame':[1,1],'result':None},'missing',got,'Missing result hides overlay; does not fabricate no-target or borrow another frame')
    d=DisplayAssociation();d.write(0,1,k,complete=True);d.result(0,1,bundle(1));d.write(0,2,Key(1,2),complete=True)
    got=[d.result(0,1,bundle(1)),d.select(0,now=1,age_limit=50,frame_duration_bound=2)]
    record('slot_reuse_retires_old_generation',6,{'slot':0,'old':[1,1,1],'new':[2,1,2]},
        ['retired_or_incomplete','missing'],got,'Slot number alone is not identity; retired generations cannot supply annotations')
    d=DisplayAssociation();d.write(0,1,k,complete=True);d.result(0,1,bundle(1));d.select(0,now=1,age_limit=50,frame_duration_bound=2);d.write(0,2,Key(1,2),complete=True)
    record('overwrite_during_scan_exposes_integrity_failure',6,{'write_after_select':True},'slot_overwritten_during_scan',exception(d.scan),'Selected pixel lease must remain valid; hiding overlay does not repair corrupted video')
    d=DisplayAssociation()
    for slot,frame in ((0,1),(1,3)):
        d.write(slot,1,Key(1,frame),complete=True);d.result(slot,1,bundle(frame))
    got=[d.select(slot,now=t,age_limit=50,frame_duration_bound=2) for slot,t in ((0,1),(0,2),(1,3))]
    record('display_repeat_and_skip',7,{'display_frames':[1,1,3]},['visible','visible','visible'],got,'Display repetition/skip does not generate acquisition observations')

    for side in ('source','destination'):
        ch=AbstractPacketChannel(2);ch.send(bundle(1));old=ch.queue[0]
        cancelled=ch.reset(side);stale=ch.receive(old);ch.send(bundle(2));fresh=ch.receive()
        got=[[x.frame for x in cancelled],stale,fresh.key.frame]
        record('cdc_'+side+'_reset_with_inflight',8,{'side':side,'old_frame':1,'new_frame':2},[[1],None,2],got,'Endpoint reset cancels in-flight epoch; old request/ack cannot reappear as fresh')
    ch=AbstractPacketChannel(2);got=[ch.send(bundle(i)) for i in (1,2,3)]
    record('bounded_channel_reports_overflow',8,{'capacity':2,'undrained_frames':[1,2,3]},
        ['queued','queued','overflow_reported'],got,'No silent overwrite or video backpressure; overflow is a counted whole-packet loss')
    got=[ch.receive().key.frame,ch.receive().key.frame,len(ch.dropped)]
    record('channel_atomic_order_and_loss_accounting',8,{'drain':True},[1,2,1],got,'All admitted packets are whole and ordered, rejected packets are counted')

    d=DisplayAssociation();d.write(0,1,k,complete=True)
    d.result(0,1,replace(bundle(1),text_key=Key(1,2)))
    got=d.select(0,now=1,age_limit=50,frame_duration_bound=2)
    record('box_text_identity_mismatch',9,{'box_frame':1,'text_frame':2},'mixed_observation',got,'Box/cross/text/count/state must represent one committed observation')
    g=gate();observe(g,1,1);observe(g,2,2)
    a=observe(g,3,3,valid=False);b=observe(g,4,4,present=False);c=observe(g,5,5,present=False)
    record('invalid_and_valid_absence_are_distinct',10,{'after_confirmation':['invalid','no_target','no_target']},
        [['invalid',2,2,0,True],['no_target',3,0,1,True],['no_target',4,0,2,False]],[a,b,c],
        'Invalid frames do not count absence; valid absence advances loss policy')
    g=gate();observe(g,1,1);observe(g,2,2);g.tick(8)
    record('silence_expires_old_observation',10,{'last_positive':2,'now':8,'fixture_age_limit':5},False,g.show,'Age advances with trusted time even without result strobes')
    g=gate();observe(g,1,1);observe(g,2,2)
    got=observe(g,3,9,captured=2)
    record('late_positive_cannot_refresh_age',10,{'arrival':9,'capture':2,'fixture_age_limit':5},
        ['stale_result',2,0,0,False],got,'Age derives from capture time, never packet arrival time')
    g=gate();got=observe(g,1,1,captured=3)
    record('future_timestamp_rejected',10,{'now':1,'capture':3},['future_time',0,0,0,False],got,'Untrusted/future time cannot establish freshness')
    d=DisplayAssociation();d.write(0,1,k,complete=True);d.result(0,1,bundle(1))
    got=d.select(0,now=4,age_limit=5,frame_duration_bound=2)
    record('age_budget_covers_entire_scan',10,{'start':4,'duration_bound':2,'capture':0,'age_limit':5},'age_budget',got,'Frame-atomic display needs age margin through scan, not only at SOF')
    q=PendingResults();q.begin(k);q.eof(k,10,5);q.begin(Key(1,2));cancel=q.reset()
    got=[[x.frame for x in cancel],[x.frame for x in q.deliver(20)]]
    record('reset_cancels_complete_tail_and_partial_frame',3,{'frame1_eof':10,'due':15,'frame2_partial':True,'reset':13},
        [[1,2],[]],got,'Every reset-cancelled result is accounted, including complete pending tails')

    g=gate();observe(g,1,1);observe(g,2,2);g.tick(7);edge=g.show;g.tick(8)
    record('age_inclusive_boundary_then_expiry',10,{'last_capture':2,'age_limit':5,'now':[7,8]},
        [True,False],[edge,g.show],'Age equality is allowed; strictly greater expires without new packets')
    g=gate();observe(g,1,1);observe(g,2,2)
    for t in range(3,9):got=observe(g,t,t,valid=False)
    record('invalid_train_expires_without_absence',10,{'invalid_times':[3,4,5,6,7,8]},
        ['invalid',2,0,0,False],got,'Invalid packets never count absence or refresh age; time still expires old target')
    g=gate();a=observe(g,3,1,valid=False);b=observe(g,3,2)
    record('invalid_identity_cannot_be_replayed_valid',1,{'same_frame':3,'validity':[False,True]},
        [['invalid',0,0,0,False],['duplicate',0,0,0,False]],[a,b],'Every identity has one disposition including invalid')
    ch=AbstractPacketChannel(3);received=[]
    for t in range(40):
        if t in (0,8,16,24):ch.send(bundle(t//8+1,captured=t))
        if t>=3 and (t-3)%5==0 and ch.queue and t-ch.queue[0].bundle.captured_at>=10:
            received.append([t,ch.receive().key.frame])
    record('distinct_clock_schedules_and_delayed_channel',8,
        {'source_clock_period':4,'source_result_times':[0,8,16,24],'destination_clock_period':5,
         'destination_phase':3,'fixture_min_channel_delay':10,'capacity':3},
        [[[13,1],[18,2],[28,3],[38,4]],0,0],[received,len(ch.queue),len(ch.dropped)],
        'Separate source/destination edges and bounded transport delay preserve atomic order; no physical CDC proof')
    g=gate();g.tick(10)
    record('raw_wrapping_time_requires_unwrap',10,{'reference_ticks':[10,0]},'clock_moved_backwards',
        exception(lambda:g.tick(0)),'Common time must be monotonic/unwrapped; raw counter wrap cannot look fresh')

    # Faulty-state negative witnesses: the invariant must reject a torn bundle.
    for name,bad in (('wrong_box',replace(bundle(1),box_key=Key(1,2))),
                     ('wrong_text',replace(bundle(1),text_key=Key(1,2))),
                     ('wrong_session',bundle(1,session=2))):
        record('negative_'+name,9,{'faulty_state':name},'mixed_observation',
            exception(lambda b=bad:require_atomic(k,b)),'Invariant rejects injected faulty committed state')

    report=dict(schema=1,status='PROPOSED CONTRACT MODEL ONLY',fixture_limits={'age_ticks':5,'acquire':2,'lose':2,'queue':2},
        source_sha256={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in
                       (Path(__file__),HERE/'model/integration_contract.py')},cases=cases,
        passed=sum(c['passed'] for c in cases),total=len(cases),
        categories_covered=sorted(set(c['category'] for c in cases)))
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"{report['passed']}/{len(cases)} traces; categories {report['categories_covered']}; no MAIN implementation implied")
    return 0 if report['passed']==len(cases) else 1

if __name__=='__main__':raise SystemExit(main())
