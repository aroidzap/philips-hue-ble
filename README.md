# Install
```
conda create -n hue python=3.9
conda activate hue
pip install bleak>=0.19.5
```

# Run
```
conda activate hue
python hue.py
python hue.py --help
```

# Requirements
- Philips Hue White And Color Ambiance A67 (or similar)
- Windows/Linux/MacOS with Bluetooth LE capability
- Paired (Bluetooth) Philips Hue (Hue App > Settings > Voice Assistants > Google Home > Make Visible, then pair on PC)
