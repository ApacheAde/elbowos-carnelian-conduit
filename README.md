# Carnelian Conduit

Full-colour Python 3 neon pipe-flow arcade for ElbowOS.

Rotate neon pipes to guide the magenta flow from top to bottom.
Collect score as the conduit advances. Leaks drop the score.

Arrow keys / WASD move the selector. Space rotates the selected pipe. R restarts.

## Play

```bash
pip install -r requirements.txt
python3 carnelian_conduit.py --play
```

## Record a 9:16 reel

```bash
python3 carnelian_conduit.py --record
```

Writes a 1080x1920 h264 clip (15s @ 30fps) with title, score, and `x.com/ElbowOS` burned into the frames.

- Featured account: https://x.com/ElbowOS
- Drive reel: https://drive.google.com/file/d/1Wd7ybEMUkYOB1A0eVQp4IrIVJ5e6o3gz/view
- GitHub: https://github.com/ApacheAde/elbowos-carnelian-conduit

Original pipe-flow mechanic. Not a clone of commercial titles.
