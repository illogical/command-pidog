# PiDog Voice Phrases & Interaction Guide

A thorough reference of natural language phrases you can say to your AI agent to control the PiDog robot. Organized by capability, with clever scenarios at the end.

---

## Movement & Navigation

```
"Walk forward."
"Move forward for a bit."
"Take a few steps forward."
"Back up."
"Walk backward."
"Retreat!"
"Turn left."
"Turn right."
"Do a U-turn."
"Spin around."
"Stop!"
"Freeze!"
"Emergency stop."
"Stay."
"Come here." → forward until proximity sensor triggers
"Go away." → backward
"Walk in a square."
"Patrol the room." → walk + turn right × 4
"Circle around."
"Explore the area." → autonomous forward/turn sequence
```

---

## Basic Postures

```
"Sit down."
"Sit, boy."
"Have a seat."
"Stand up."
"On your feet."
"Lie down."
"Roll over." → lie
"Lay flat."
"Play dead." → lie + doze off
"Get up."
"Be ready." → stand
```

---

## Tricks & Stunts

```
"Shake hands."
"Shake."
"Give me your paw."
"High five!"
"Slap me five."
"Do a push-up."
"Show me your muscles."
"Work out."
"Stretch."
"Do your morning stretch."
"Twist your body."
"Do a stretch routine." → stretch + twist body + relax neck
"Relax your neck."
"Roll your neck."
"Scratch yourself."
"Scratch that itch."
"Do a trick."
"Show off." → stand + stretch + sit + handshake
"Impress me." → full performance sequence
"Do your best trick." → chain of impressive actions
```

---

## Emotions & Expressions

```
"Bark!"
"Say hello." → wag tail + bark
"Bark louder!"
"Growl at me." → bark harder
"Attack position." → bark harder
"Wag your tail."
"Are you happy?" → wag tail + pant
"Show me you're excited." → wag tail + bark + boom yellow LEDs
"Pant."
"Be happy."
"Howl at the moon." → howl
"Sing for me." → howl
"Howl!"
"Shake your head."
"Say no." → shake head
"Nod."
"Say yes." → nod
"Think about it." → think
"You look confused." → think
"Remember something." → recall
"Try to remember." → recall
"Panic!" → fluster
"You're flustered." → fluster
"Be surprised." → surprise
"Act startled." → surprise
"React like you saw a ghost." → surprise + bark
"Be scared." → surprise + shake head
```

---

## Affection & Social

```
"Lick my hand."
"Give me some love."
"Be sweet."
"Be affectionate." → lick hand + wag tail + pink breath LEDs
"Welcome me home." → wag tail + bark + pant
"Say goodbye." → wag tail + nod
"Meet my friend." → sit + handshake
"Introduce yourself." → stand + bark + sit + handshake
"Play with me." → pant + wag tail
"Pet yourself." → scratch
"Are you tired?" → doze off or lie
"Go to sleep." → lie + doze off + magenta breath LEDs
"Wake up!" → stand + bark
"Good morning!" → stand + stretch + bark
"Goodnight." → lie + doze off + magenta breath
```

---

## Sensor Queries

```
"How far is the nearest obstacle?"
"What's in front of you?"
"Is anything close to you?"
"What's the distance reading?"
"How are you tilted?"
"Are you level?"
"What's your pitch?"
"What's your roll?"
"Is anything touching you?"
"Am I petting you?"
"Where is that sound coming from?"
"What direction is the noise?"
"Did you hear something?"
"How's your battery?"
"What's your battery level?"
"Are you running low?"
"How long have you been running?"
"What's your status?"
"Give me a full health report."
"Are you okay?"
"Check your sensors."
```

---

## Visual Perception (Camera)

```
"What do you see?"
"Look around."
"Describe the room."
"What's in front of you?"
"Is there anyone there?"
"Who's in the room?"
"Can you see me?"
"Take a look." → POST /agent/vision
"Check if the path is clear."
"Are there any obstacles?"
"What color is that thing in front of you?"
"Is it safe to move forward?"
"Tell me what's on the floor."
"Look for my keys."
"Do you see any toys?"
"Describe what you see."
"What can you see from there?"
"Is anyone waving at you?"
"React to what you see." → vision + auto-execute suggested actions
"Take a snapshot."
"Give me a camera snapshot." → GET /camera/snapshot
"Start the camera."
"Turn on your camera."
"Stop the camera."
"Show me the live feed." → GET /camera/stream
"What time of day does it look like?"
"How bright is the room?"
"Describe the scene in one sentence."
```

---

## LED Control

```
"Turn your lights blue."
"Set your LEDs to red."
"Make your chest glow green."
"Show me a breathing light."
"Do the breath effect in cyan."
"Pulse your lights."
"Flash your lights." → boom style
"Bark with your lights." → bark style, red
"Show listening mode." → listen style, green
"Show speaking mode." → speak style, cyan
"Turn off your lights."
"Lights off."
"Set mood lighting." → breath, magenta, low bps
"Alert mode." → monochromatic yellow
"Emergency lights." → bark style, red, fast bps
"Happy lights." → breath, cyan
"Angry lights." → bark, red
"Sleepy lights." → breath, magenta
"Party mode." → boom, yellow, fast bps
"Rainbow mode." → cycle through colors (if supported)
```

---

## Sound

```
"Bark once."
"Make a sound."
"Play a sound."
"Howl."
"Make the bark sound."
"Be quiet." → stop sound
"Say something." → TTS
```

---

## Servo Fine Control

```
"Turn your head left."
"Look to the right."
"Look up."
"Look down."
"Tilt your head."
"Face me." → yaw toward sound or camera center
"Look left 45 degrees." → yaw: -45
"Look up a bit." → pitch: -20
"Center your head." → yaw: 0, roll: 0, pitch: 0
"Wag your tail 60 degrees."
"Wag faster." → rapid tail oscillation
"Point your nose up."
```

---

## AI Interaction & Personality

```
"Tell me something interesting."
"Make me laugh."
"Tell a joke."
"What are you thinking?"
"What's on your mind?"
"Are you bored?"
"Do something random." → pick a random action
"Surprise me." → random sequence
"What can you do?"
"Show me all your tricks."
"What's your name?"
"Who made you?"
"Are you a real dog?"
"How smart are you?"
"Prove you're intelligent."
"Solve a math problem." → any math question
"What time is it?" → check system clock
"Tell me about yourself."
"What do your sensors say right now?"
"Read me your status."
"What's happening around you?"
```

---

## Voice Pipeline

```
[Speak into microphone after triggering wake word]
→ POST /agent/voice (audio file)
→ Whisper STT transcribes
→ POST /agent/chat with transcription
→ Actions executed + TTS plays response

"Hey PiDog, walk forward."
"Hey PiDog, what do you see?"
"Hey PiDog, shake hands with my friend."
"Hey PiDog, go to sleep."
"Hey PiDog, how's your battery?"
"Hey PiDog, do a push-up."
```

---

## Clever Scenarios & Show-Off Moments

### The Grand Entrance
> "Introduce yourself dramatically."

Expected: Stand, bark, sit, high five, spin, howl — with yellow boom LEDs and a witty spoken intro.

---

### The Obstacle Guardian
> "Watch the doorway and warn me if someone enters."

Expected: Camera starts, PiDog faces door, loops `/agent/vision` every 30s, barks and alerts when a person is detected.

---

### The Fitness Instructor
> "Lead me through a workout."

Expected: PiDog does push-ups while narrating ("One! Two! Three! You're not doing yours, are you?"), then stretches.

---

### The Security Dog
> "Patrol the perimeter and report back."

Expected: Walk forward → turn right × 4, take a vision snapshot at each corner, return a narrated security report.

---

### The Sommelier
> "Look at this drink and tell me what you think."

Expected: `/agent/vision` with question "Describe this beverage and give it a witty rating." PiDog inspects and narrates.

---

### Sound Hunting
> "Find where that noise is coming from."

Expected: Poll `/sensors/sound`, use yaw servo to turn head toward the detected direction, then body turn if angle > 45°.

---

### The Empath
> "How are you feeling right now?"

Expected: Read battery, distance, IMU, touch → synthesize an emotional state → perform matching action + LED.
- High battery + no obstacles → excited (boom yellow) + wag tail
- Low battery → sleepy (magenta breath) + doze off
- Something close → alert (yellow mono) + think

---

### The Loyal Greeter
> "Wait by the door and greet the next person who comes in."

Expected: Stand idle at door (waiting action loop), vision-poll every 10s, when a person is detected → bark + wag tail + sit + handshake.

---

### The Yoga Instructor
> "Do a full body stretch routine."

Expected: Stand → stretch → twist body → sit → relax neck → sit rest. TTS narrates each pose.

---

### The Storyteller
> "Tell me a story and act it out."

Expected: LLM generates a short story and maps it to actions/sounds:
- "Once upon a time..." → think
- "...the brave dog heard a noise..." → head toward sound direction
- "...and barked fiercely!" → bark harder
- "...then fell fast asleep." → lie + doze off + magenta LEDs

---

### The Science Experiment
> "How does your IMU respond when I tilt you?"

Expected: Stream IMU data via WebSocket, PiDog reads values aloud as you tilt it, reacts to unusual angles with `surprise` or `fluster`.

---

### The Personal Trainer Check-In
> "Do 5 push-ups and count them out loud."

Expected: Loop `["stand", "push up"]` × 5, TTS says "One!", "Two!" etc. End with `["sit", "pant"]` and "All done! Now it's your turn."

---

### Vision + Action Fusion
> "Look at what's in front of you and react appropriately."

Expected: `/agent/vision` → if person → wag tail + handshake; if ball → pant + forward; if obstacle → backward + alert LEDs; if nothing → waiting + "Nothing to report, Captain."

---

## WebSocket Live Dashboard

Subscribe once, get everything in real time:

```javascript
ws.send(JSON.stringify({
  "type": "subscribe",
  "channels": ["sensors", "action_status", "status", "logs"]
}));
```

Use the stream to:
- Show a live obstacle distance meter
- Trigger automated reactions (bark when distance < 20 cm)
- Display battery gauge
- Show a live activity log
- Build a dashboard that shows posture + LED state
