# LoRa Image Transmission Research System

A comprehensive Python-based system for transmitting images over LoRa networks using RAK3172 modules. Designed for research applications requiring reliable long-range image transmission with detailed performance analysis.

## 🚀 Features

### Core Capabilities
- **Original Resolution Transmission**: Send images without any resizing
- **Smart Image Optimization**: Automatic resizing for faster transmission
- **Batch Processing**: Send multiple images sequentially
- **Text Message Testing**: Quick connectivity verification
- **Real-time Performance Monitoring**: RSSI, SNR, and timing analysis
- **Research-Grade Logging**: Comprehensive statistics for analysis

### Hardware Support
- **RAK3172 LoRa Modules**: Optimized for RAK3172-E with RUI 4.2.0
- **USB-UART Interface**: CH340/CH341 compatible
- **Camera Integration**: OpenCV-based camera capture
- **Multi-format Support**: JPG, PNG, BMP, TIFF image formats

## 📋 Requirements

### Hardware
- **2x RAK3172 LoRa modules** 
- **2x USB-UART converters** 
- **1x Camera** (USB webcam or built-in) - optional for pre-captured images
- **2x Computers/devices** for TX and RX operation

### Software Dependencies
```bash
pip install opencv-python pyserial numpy matplotlib pandas pillow openpyxl
```

## 🛠 Installation

1. **Clone or download** the project files:
   ```
   lora_transmitter_only.py
   lora_receiver_only.py
   ```

2. **Connect hardware**:
   - Connect RAK3172 modules to USB-UART converters
   - Connect USB-UART converters to computers
   - Note the COM ports (e.g., COM10, COM11)

3. **Prepare test images** (optional):
   - Create folder `test_images/`
   - Copy your images (JPG, PNG, BMP, TIFF)

## 🚀 Quick Start

### Step 1: Start Receiver (Device 2)
```bash
python lora_receiver_only.py
Enter Receiver COM port: COM11
📡 Starting LoRa image receiver...
🎯 Waiting for incoming image transmissions...
```

### Step 2: Start Transmitter (Device 1)
```bash
python lora_transmitter_only.py
Enter Transmitter COM port: COM10

🎯 Choose operation mode:
1. Send pre-captured images from folder (no camera needed)
2. Capture new images with camera and send
Enter choice: 1

🚀 Transmitter ready!
```

### Step 3: Test Connection
```bash
Transmitter> test
Test message> Hello World
📤 Sent string: 'Hello World'
✅ String transmission successful!
```

Receiver should show:
```bash
💬 Text Message: 'Hello World' (RSSI=-73dBm, SNR=-14dB)
```

### Step 4: Send Images
```bash
Transmitter> scan                    # View available images
Transmitter> original                # Send at original resolution
Enter image number: 0
Enter quality: 85
```

## 📖 Commands Reference

### Transmitter Commands

| Command | Description |
|---------|-------------|
| `help` | Show all available commands |
| `help <command>` | Detailed help for specific command |
| `test` | Send text strings to test LoRa connection |
| `folder` | Set custom image folder path |
| `scan` | Analyze all images in current folder |
| `original` | Send image at ORIGINAL resolution (no resizing) |
| `batch` | Send multiple images sequentially |
| `send` | Capture and send from camera (camera mode only) |
| `capture` | Capture and save image (camera mode only) |
| `stats` | Show transmission statistics |
| `quit` | Exit program |

### Detailed Command Examples

#### Testing LoRa Connection
```bash
Transmitter> test
Test message> TX1 Ready
Test message> Signal Test 123
Test message> back           # Return to main menu
```

#### Folder Management
```bash
Transmitter> folder
Current folder: C:\project\test_images
Enter new path: C:\MyResearchPhotos
✅ Image folder changed

Transmitter> scan
📊 Found 15 images in folder
 0: IMG_001.jpg    2,847KB  4032x3024  12.2MP
 1: photo_hd.jpg   1,543KB  1920x1080   2.1MP
⏱️  Estimated total time: ~147 minutes
```

#### Sending Original Resolution Images
```bash
Transmitter> original
Enter image number: 0
Enter quality (default 85): 90
📏 ORIGINAL Resolution: 4032x3024 pixels
⏱️  Estimated transmission: ~87.3 minutes
Continue? y
```

#### Batch Processing
```bash
Transmitter> batch
Enter start image (0-14): 0
Enter end image (0-14): 2
Enter quality (default 85): 80
Send at (o)riginal or (r)esized? o
🚀 Will send 3 images from index 0 to 2
Start batch transmission? y
```

## 📊 Performance Analysis

### Real-time Monitoring
The system provides comprehensive performance data:

**Transmission Metrics:**
- Duration per image
- Fragment success rate
- Data throughput (Kbps)
- Estimated vs actual timing

**Signal Quality Analysis:**
- RSSI (Received Signal Strength Indicator)
- SNR (Signal-to-Noise Ratio)
- Signal stability over time
- Quality distribution analysis

**Reception Statistics:**
- Image reconstruction success rate
- Fragment loss analysis
- Signal quality trends

### Generated Reports
After transmission sessions, the system generates:
- **Performance plots** (PNG files)
- **Detailed reports** (TXT files)  
- **Raw data** (Excel files)

Perfect for research papers and analysis!

## 🔬 Research Applications

### Typical Use Cases
- **Environmental Monitoring**: Remote camera networks
- **Agricultural Research**: Field monitoring systems
- **Security Systems**: Long-range surveillance
- **IoT Networks**: Low-power image transmission
- **Disaster Response**: Emergency communication systems

### Experimental Parameters
- **Distance Testing**: Measure performance vs range
- **Image Quality Analysis**: Original vs compressed transmission
- **Environmental Impact**: Weather/obstacle effects on signal
- **Network Scaling**: Multiple transmitter scenarios

## ⚙️ Configuration Options

### Image Quality Settings
- **Quality 30-50**: Fast transmission, lower quality
- **Quality 60-80**: Balanced performance
- **Quality 85-100**: High quality, slower transmission

### Resolution Modes
- **Original**: No resizing, maximum quality
- **Auto-optimized**: Smart resizing for LoRa
- **Custom**: User-defined dimensions

### LoRa Parameters (RAK3172)
- **Frequency**: 868MHz (configurable)
- **Spreading Factor**: 7 (fast) to 12 (long range)
- **Bandwidth**: 125kHz
- **TX Power**: Up to 20dBm

## 🐛 Troubleshooting

### Common Issues

**"Module not responding"**
- Check COM port connection
- Verify USB-UART driver installation
- Try different baud rates (115200, 57600, 9600)

**"Camera not initialized"**
- Check camera index (0, 1, 2...)
- Verify camera permissions
- Try different camera if multiple available

**"Image too large error"**
- Reduce JPEG quality (try 60-80%)
- Use auto-resize mode instead of original
- Maximum: 65535 fragments per image

**"Fragment loss/poor reception"**
- Check RSSI values (should be > -100dBm)
- Reduce distance between TX/RX
- Check for obstacles/interference
- Verify antenna connections

### Signal Quality Guide
- **RSSI > -70dBm**: Excellent signal 🟢
- **RSSI -70 to -85dBm**: Good signal 🟡
- **RSSI -85 to -100dBm**: Fair signal 🟠  
- **RSSI < -100dBm**: Poor signal 🔴

## 📝 Research Documentation

### For Academic Papers
The system generates research-grade data including:
- Statistical analysis of transmission performance
- Signal quality vs distance relationships
- Image quality vs transmission time trade-offs
- Network reliability metrics

### Data Export Formats
- **Excel**: Raw performance data
- **PNG**: Professional plots and graphs
- **TXT**: Detailed statistical reports

## 🔄 Future Enhancements

### Planned Features
- **Multi-node Networks**: Round-robin transmission scheduling
- **Adaptive Quality**: Dynamic quality based on signal strength
- **Error Correction**: Advanced packet recovery mechanisms
- **Real-time Monitoring**: Live performance dashboard

## 📞 Support

### Getting Help
1. Use `help <command>` for detailed command information
2. Check troubleshooting section for common issues
3. Verify hardware connections and COM ports
4. Test with simple text messages before images

### System Requirements
- **Python 3.7+**
- **Windows/Linux/macOS** compatible
- **2GB RAM** minimum
- **USB ports** for LoRa modules

---

## 📄 License

This system is designed for research and educational purposes. Please ensure compliance with local LoRa frequency regulations.
