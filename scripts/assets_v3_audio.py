"""Original 96 BPM celesta/flute cue; no samples from the reference recording."""
from pathlib import Path
import json
import wave
import math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'app/src/main/assets/v3/audio'; OUT.mkdir(parents=True,exist_ok=True)
SR=32000
def write(name,data):
    data=np.clip(data,-.95,.95)
    with wave.open(str(OUT/(name+'.wav')),'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((data*32767).astype('<i2').tobytes())
def note(midi,duration,kind='bell'):
    t=np.arange(int(SR*duration))/SR; hz=440*2**((midi-69)/12)
    if kind=='flute':
        signal=np.sin(2*np.pi*hz*t+.002*np.sin(t*30))*np.minimum(t/.09,1)*np.minimum((duration-t)/.18,1)
        signal+=.15*np.sin(2*np.pi*hz*2*t)*np.minimum(t/.1,1)*np.exp(-t*2)
    else:
        signal=(np.sin(2*np.pi*hz*t)*np.exp(-t*2.5)+.32*np.sin(2*np.pi*hz*2.002*t)*np.exp(-t*5)+.12*np.sin(2*np.pi*hz*3*t)*np.exp(-t*8))*np.minimum(t/.008,1)
        signal*=np.minimum((duration-t)/.04,1)
    return signal
def add(track,start,signal,level,pan=0):
    indices=(np.arange(len(signal))+int(start*SR))%len(track)
    track[indices,0]+=signal*level*np.sqrt((1-pan)/2)
    track[indices,1]+=signal*level*np.sqrt((1+pan)/2)

beat=.625; duration=64*beat
music=np.zeros((int(SR*duration),2))
chords=[(60,64,67),(57,60,64),(53,57,60),(55,59,62)]*4
melody=[(76,0,1.5),(79,2,1),(81,3,1),(79,4,2),(76,6,1),(74,7,1),
        (72,8,1.5),(76,10,1),(79,11,1),(77,12,2),(76,14,1),(74,15,1)]
for bar,chord in enumerate(chords):
    for n in range(8):
        pitch=chord[[0,1,2,1,0,2,1,2][n]]+12
        add(music,(bar*4+n*.5)*beat,note(pitch,1.4),.07 if n%2 else .095,(-.32 if n%2 else .32))
    add(music,bar*4*beat,note(chord[0]-12,2.6,'flute'),.055)
for section in range(4):
    for pitch,start,length in melody:
        add(music,(section*16+start)*beat,note(pitch,beat*length,'flute'),.085, .12 if section%2 else -.12)
# A small circular stereo echo preserves continuity at the loop boundary.
music+=np.roll(music,int(SR*.235),axis=0)[:,::-1]*.18
write('music',music)
arrival=np.zeros((int(SR*2.3),2))
for i,pitch in enumerate([79,84,88,91]): add(arrival,i*.13,note(pitch,1.65),.18-.018*i,(i-1.5)*.2)
write('arrival',arrival)
(OUT/'provenance.json').write_text(json.dumps({'author':'BugWorld procedural score','tempoBpm':96,'durationSeconds':duration,'instruments':'original synthesized celesta, flute and soft bass','referenceTrackIdentified':False,'recordingReused':False},indent=2),encoding='utf-8')

# Retained original natural/interaction sounds; the only active audio build script.
rate=22050; seconds=48; t=np.arange(rate*seconds)/rate
noise=np.random.default_rng(123).normal(0,1,len(t))
water=np.tanh(np.convolve(noise,np.ones(17)/17,mode='same'))*.10*(.7+.3*np.sin(math.tau*t/12))
fade=np.minimum(1,np.minimum(t/.12,(seconds-t)/.12))
touch_time=np.arange(int(rate*.55))/rate
touch=.11*np.sin(math.tau*880*touch_time)*np.exp(-touch_time*9)*(1-np.exp(-touch_time*80))
for name,samples in [('stream',water*fade),('touch',touch)]:
    with wave.open(str(OUT/(name+'.wav')),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        f.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
