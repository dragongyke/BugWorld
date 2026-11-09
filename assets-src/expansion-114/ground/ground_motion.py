"""Action authoring portion of build_ground.py. Bone rest axes match world axes."""
def axis(which,degrees):
    return Quaternion({'x':(1,0,0),'y':(0,1,0),'z':(0,0,1)}[which],math.radians(degrees))


def bell(t,a,b):
    x=min(1,max(0,(t-a)/(b-a)))
    return math.sin(math.pi*x)**2


def smoothstep(t,a,b):
    x=min(1,max(0,(t-a)/(b-a)))
    return x*x*(3-2*x)


def solve_leg(points,fi,ti,ai,target):
    hip,knee,ankle=[wp(points[i]) for i in [fi,ti,ai]]
    seg_a=knee-hip;seg_b=ankle-knee
    length_a=seg_a.length;length_b=seg_b.length
    aim=(target-hip).normalized()
    distance=max(abs(length_a-length_b)+.00001,min((target-hip).length,length_a+length_b-.00001))
    sagittal=seg_a-aim*seg_a.dot(aim);sagittal.normalize()
    along=(length_a**2-length_b**2+distance**2)/(2*distance)
    joint=hip+aim*along+sagittal*math.sqrt(max(0,length_a**2-along**2))
    femur=seg_a.rotation_difference((joint-hip).normalized())
    shank=seg_b.rotation_difference((hip+aim*distance-joint).normalized())
    return femur,femur.inverted()@shank,shank.inverted()


clips=({'idle':73,'walk':25,'touch':29,'explore':61,'groom':73} if ANT_MODE else
       {'idle':73,'walk':31,'takeoff':25,'flight':25,'touch':31,'perch':49,'hop':37})
rig.animation_data_create()
for clip,end in clips.items():
    action=bpy.data.actions.new(clip);action.use_fake_user=True
    rig.animation_data.action=action
    last={}
    for frame in range(1,end+1):
        t=(frame-1)/(end-1);w=math.tau*t;sw=math.sin(w)
        pulse=bell(t,.03,.93)
        crouch=bell(t,.00,.33) if clip in ('hop','takeoff') else 0
        air=(bell(t,.23,.89) if clip=='hop' else smoothstep(t,.28,.75) if clip=='takeoff' else 1 if clip=='flight' else 0)
        land=bell(t,.77,1) if clip=='hop' else 0
        rootz=0
        if clip=='idle':rootz=.65*(1-math.cos(w))
        if clip=='walk':rootz=1.6*(1-math.cos(2*w))
        if clip=='perch':rootz=-5*math.sin(w/2)**2
        if clip in ('hop','takeoff'):rootz=-14*crouch+25*air-7*land
        if clip=='flight':rootz=25+2.5*math.sin(3*w)
        if clip=='touch':rootz=-8*bell(t,0,.44)+3*bell(t,.44,.84)
        if clip=='groom':rootz=-3*pulse
        rootloc=Vector((0,0,rootz*UNIT))
        rot={}
        if clip=='idle':
            rot[head]=axis('z',2.5*sw)@axis('y',1.9*math.sin(2*w));rot[abd]=axis('y',1.8*sw)
        if clip=='walk':
            rot[head]=axis('y',2.5*math.sin(2*w));rot[abd]=axis('z',2.8*sw)
        if clip=='explore':
            rot[head]=axis('z',13*sw)@axis('y',9*pulse);rot[abd]=axis('z',-4*sw)
        if clip=='groom':
            rot[head]=axis('z',-11*pulse)@axis('y',9*pulse)
        if clip=='touch':
            rot[head]=axis('y',-14*bell(t,.02,.52))@axis('z',6*bell(t,.44,.94))
            rot[abd]=axis('y',-6*bell(t,.02,.52))
        if clip in ('hop','takeoff','flight','perch'):
            rot[head]=axis('y',-4*air+4*crouch+2*sw)
            rot[abd]=axis('y',-3*air+3*crouch)
        for side in (-1,1):
            if clip=='explore':sweep=side*(23*sw+9*math.sin(2*w));dip=14*pulse
            elif clip=='groom':sweep=-side*21*pulse;dip=side*7*math.sin(3*w)*pulse+13*pulse
            elif clip=='touch':sweep=side*27*bell(t,0,.53);dip=-14*bell(t,.02,.51)
            else:sweep=side*(5*sw if clip=='idle' else 3*math.sin(2*w));dip=2*sw
            rot['Scape '+str(side)]=axis('z',sweep)@axis('y',dip)
            rot['Flagellum '+str(side)]=axis('z',sweep*.52)@axis('y',dip*.72)
            if not ANT_MODE:
                deploy=(1 if clip=='flight' else smoothstep(t,.53,.94) if clip=='takeoff' else 0)
                lift=(1 if clip=='flight' else smoothstep(t,.43,.85) if clip=='takeoff' else 0)
                flap=(math.sin(3*w) if clip=='flight' else math.sin(3*w)*air)
                rot['Tegmen '+str(side)]=axis('z',-side*31*deploy)@axis('y',15*lift)@axis('x',side*(53+9*flap)*lift)
                for lobe in range(3):
                    rot[f'Fan {side} sector {lobe}']=axis('z',-side*(46+lobe*12)*deploy)@axis('y',14*lift)@axis('x',side*(64+27*flap)*lift)
        lowest_tarsus=float('inf')
        for side,num,points,fi,ti,ai,coxa,femur,tibia,toe in legs:
            # Root-relative ankle targets keep the feet planted while crouching
            # and make the jumping femur and spined tibia visibly extend apart.
            ankle=wp(points[ai]); delta=Vector((0,0,0))
            if clip=='walk':
                phase=w+(math.pi if (num+int(side>0))%2==0 else 0)
                delta.x=UNIT*(16 if ANT_MODE else 12)*math.sin(phase)
                delta.z=UNIT*max(0,math.cos(phase))*10
            if clip=='touch' and num==0:
                delta.x=UNIT*9*pulse;delta.z=UNIT*12*pulse
            if clip=='explore' and num==0:
                delta.x=UNIT*7*bell(t,.12,.65);delta.z=UNIT*10*bell(t,.12,.65)
            if clip=='groom' and num==0 and side==1:
                delta.x=UNIT*(70+5*math.sin(3*w))*pulse
                delta.y=-UNIT*33*pulse;delta.z=UNIT*(100+9*math.sin(3*w))*pulse
            if clip in ('flight','takeoff','hop'):
                if num==2:
                    # The jumping legs extend aft at launch, then fold before landing.
                    delta.x=-UNIT*(78 if clip=='hop' else 51)*air
                    delta.z=UNIT*(17 if clip=='hop' else 40)*air
                else:
                    delta.x=-UNIT*16*air;delta.z=UNIT*35*air
                if clip!='flight':delta.z+=max(0,rootloc.z)*air
            if clip=='perch' and num==2:delta.x=UNIT*4*pulse
            qf,qt,qfoot=solve_leg(points,fi,ti,ai,ankle+delta-rootloc)
            if num==2 and clip in ('hop','takeoff','flight'):
                # A kick extends the shank behind the animal. In flight the same
                # shank folds under the femur while tegmen and fan swing above it.
                target_femur=axis('y',-40 if clip=='hop' else -37)
                target_shank=axis('y',75 if clip=='hop' else -62)
                sweep=smoothstep(t,.24,.55) if clip=='takeoff' else air
                qf=qf.slerp(target_femur,sweep)
                qt=qt.slerp(target_femur.inverted()@target_shank,sweep)
                qfoot=qfoot.slerp(target_shank.inverted(),sweep)
            rot[femur]=qf;rot[tibia]=qt;rot[toe]=qfoot
            hip,knee=[wp(points[i]) for i in (fi,ti)]
            knee_pos=hip+qf@(knee-hip)
            ankle_pos=knee_pos+(qf@qt)@(ankle-knee)
            for pt in points[ai:]:
                pos=ankle_pos+(qf@qt@qfoot)@(wp(pt)-ankle)
                lowest_tarsus=min(lowest_tarsus,pos.z+rootloc.z)
        if air>0:
            rootloc.z+=max(0,UNIT*(2+10*air)-lowest_tarsus)
        for name in bones:
            pb=rig.pose.bones[name];pb.rotation_mode='QUATERNION'
            q=rot.get(name,Quaternion())
            if name in last:q.make_compatible(last[name])
            pb.rotation_quaternion=q;last[name]=q.copy()
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)
            if name==ROOT:
                pb.location=rootloc;pb.keyframe_insert('location',frame=frame,group=name)
    # Store a muted editable track, leaving the unanimated rest state visible.
    track=rig.animation_data.nla_tracks.new();track.name=clip
    strip=track.strips.new(clip,1,action);track.mute=True
    rig.animation_data.action=None
for pb in rig.pose.bones:pb.rotation_quaternion=Quaternion();pb.location=(0,0,0)
