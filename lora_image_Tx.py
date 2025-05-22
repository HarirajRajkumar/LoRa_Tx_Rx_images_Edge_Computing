#!/usr/bin/env python3
"""
Dedicated LoRa Image Transmitter for RAK3172
Run this script on the transmitting device
"""

import cv2
import serial
import time
import struct
import numpy as np
from datetime import datetime
import os
import glob

class RAK3172ImageTransmitter:
    """
    Dedicated transmitter for RAK3172 LoRa image transmission
    """
    def __init__(self, serial_port, baud_rate=115200, camera_index=0):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.camera_index = camera_index
        self.connection = None
        self.camera = None
        self.camera_initialized = False
        self.transmission_log = []
        self.image_folder = "test_images"  # Folder for pre-captured images
        
        # Create test images folder if it doesn't exist
        os.makedirs(self.image_folder, exist_ok=True)
        
    def initialize_hardware(self, init_camera=False):
        """Initialize LoRa connection and optionally camera"""
        try:
            # Initialize LoRa connection
            print(f"📡 Connecting to LoRa module on {self.serial_port}...")
            self.connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            # Setup RAK3172 for transmission
            self.setup_rak3172_transmitter()
            
            print(f"✅ LoRa transmitter ready on {self.serial_port}")
            
            # Initialize camera only if requested
            if init_camera:
                self.initialize_camera()
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def initialize_camera(self):
        """Initialize camera when needed"""
        try:
            print(f"🎥 Initializing camera {self.camera_index}...")
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                raise Exception(f"Could not open camera {self.camera_index}")
            
            # Set camera properties for LoRa transmission
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Higher resolution
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # Verify camera settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"✅ Camera initialized: {actual_width}x{actual_height}")
            
            self.camera_initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Camera initialization failed: {e}")
            return False
    
    def setup_rak3172_transmitter(self):
        """Setup RAK3172 for P2P transmission"""
        print("🔧 Configuring RAK3172 for transmission...")
        
        # Stop any existing RX mode
        self.connection.write(b"AT+PRECV=0\r\n")
        time.sleep(1)
        response = self.connection.read_all().decode().strip()
        
        # Configure P2P parameters
        setup_commands = [
            ("AT+NWM=0", "Set to LoRa P2P mode"),
            ("AT+PFREQ=868000000", "Set frequency to 868MHz"),
            ("AT+PSF=7", "Set spreading factor to 7 (faster)"),
            ("AT+PBW=125", "Set bandwidth to 125kHz"),
            ("AT+PCR=1", "Set coding rate to 4/5"),
            ("AT+PPL=8", "Set preamble length to 8"),
            ("AT+PTP=20", "Set TX power to 20dBm"),
        ]
        
        for cmd, description in setup_commands:
            self.connection.write(f"{cmd}\r\n".encode())
            time.sleep(0.8)
            response = self.connection.read_all().decode().strip()
            
            if "OK" in response or response == "":
                print(f"✅ {description}")
            else:
                print(f"⚠️  {description}: {response}")
        
        print("✅ RAK3172 configured for transmission")
    
    def send_test_string(self, message):
        """Send a simple text string for testing LoRa connection"""
        try:
            print(f"🧪 Testing connection with message: '{message}'")
            
            # Convert message to hex (same as RAK3172 format)
            hex_message = message.encode('utf-8').hex().upper()
            
            # Send using AT+PSEND
            cmd = f"AT+PSEND={hex_message}\r\n"
            self.connection.write(cmd.encode())
            print(f"📤 Sent test string (hex: {hex_message})")
            
            # Wait for transmission confirmation
            time.sleep(2)
            response = ""
            if self.connection.in_waiting:
                response = self.connection.read_all().decode().strip()
            
            if "+EVT:TXP2P" in response:
                print(f"✅ Test transmission confirmed (TX complete)")
                return True
            elif "OK" in response:
                print(f"✅ Test command accepted (OK response)")
                return True
            elif "AT_BUSY_ERROR" in response:
                print(f"⚠️  Module busy during test")
                return False
            elif response == "":
                print(f"✅ No error response (likely successful)")
                return True
            else:
                print(f"❌ Unexpected response: {response}")
                return False
                
        except Exception as e:
            print(f"❌ Test transmission failed: {e}")
            return False
    
    def capture_image(self, quality=50, target_size=None):
        """
        Capture image from camera with smart resizing for LoRa transmission
        """
        if not self.camera_initialized:
            print("🎥 Camera not initialized. Initializing now...")
            if not self.initialize_camera():
                raise Exception("Failed to initialize camera")
        
        if not self.camera or not self.camera.isOpened():
            raise Exception("Camera not available")
        
        ret, frame = self.camera.read()
        if not ret:
            raise Exception("Failed to capture image")
        
        original_size = (frame.shape[1], frame.shape[0])
        print(f"📸 Original image: {original_size[0]}x{original_size[1]}")
        
        # Smart resizing based on target size or automatic optimization
        if target_size:
            # Resize to specific target
            frame_resized = cv2.resize(frame, target_size)
            print(f"📏 Resized to: {target_size[0]}x{target_size[1]}")
        else:
            # Automatic optimization - balance quality vs transmission time
            # Keep aspect ratio while optimizing for LoRa
            target_pixels = 320 * 240  # Target around 76K pixels for good balance
            current_pixels = original_size[0] * original_size[1]
            
            if current_pixels > target_pixels:
                scale = (target_pixels / current_pixels) ** 0.5
                new_width = int(original_size[0] * scale)
                new_height = int(original_size[1] * scale)
                # Ensure even dimensions for better compression
                new_width = new_width - (new_width % 2)
                new_height = new_height - (new_height % 2)
                frame_resized = cv2.resize(frame, (new_width, new_height))
                print(f"📏 Auto-resized to: {new_width}x{new_height} (scale: {scale:.2f})")
            else:
                frame_resized = frame
                print(f"📏 Keeping original size: {original_size[0]}x{original_size[1]}")
        
        # Convert to JPEG with specified quality
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ret, buffer = cv2.imencode('.jpg', frame_resized, encode_param)
        
        if not ret:
            raise Exception("Failed to encode image")
        
        final_size = len(buffer)
        print(f"📦 Final size: {final_size} bytes (quality: {quality}%)")
        
        # Estimate transmission time
        estimated_fragments = (final_size + 165) // 165  # ~165 bytes per fragment
        estimated_time = estimated_fragments * 1.8  # ~1.8s per fragment
        print(f"⏱️  Estimated transmission: ~{estimated_time:.1f}s ({estimated_fragments} fragments)")
        
    def print_help(self, command=None):
        """Print detailed help for commands"""
        if command is None:
            print("\n📖 HELP - LoRa Image Transmitter Commands")
            print("=" * 50)
            print("Basic Commands:")
            print("  help <command> - Show detailed help for specific command")
            print("  folder         - Set custom image folder path")
            print("  scan          - Scan and analyze images in current folder")
            print("  original      - Send image at ORIGINAL resolution")
            print("  batch         - Send multiple images sequentially")
            print("  send          - Capture and send from camera")
            print("  stats         - Show transmission statistics")
            print("  quit          - Exit program")
            print("\nType 'help <command>' for detailed information")
            return
        
        command = command.lower()
        
        if command == 'folder':
            print("\n📁 FOLDER COMMAND")
            print("-" * 30)
            print("Purpose: Set a custom folder path for images")
            print("Usage: folder")
            print("Description:")
            print("  • Shows current image folder")
            print("  • Allows you to set new folder path")
            print("  • Automatically scans new folder for images")
            print("  • Supports any folder with JPG, PNG, BMP, TIFF files")
            print("Example:")
            print("  Transmitter> folder")
            print("  Current folder: /default/test_images")
            print("  Enter new path: C:\\MyPhotos")
        
        elif command == 'scan':
            print("\n🔍 SCAN COMMAND")
            print("-" * 30)
            print("Purpose: Analyze all images in current folder")
            print("Usage: scan")
            print("Description:")
            print("  • Shows total number of images found")
            print("  • Displays each image with details:")
            print("    - File size (KB/MB)")
            print("    - Resolution (width x height)")
            print("    - Megapixels")
            print("  • Estimates total transmission time")
            print("  • Helps you plan which images to send")
            print("Example output:")
            print("  📊 Found 5 images in folder")
            print("  0: photo1.jpg    2,847KB  4032x3024  12.2MP")
            print("  ⏱️  Estimated total time: ~147 minutes")
        
        elif command == 'original':
            print("\n🎯 ORIGINAL COMMAND") 
            print("-" * 30)
            print("Purpose: Send images at their ORIGINAL resolution")
            print("Usage: original")
            print("Description:")
            print("  • NO RESIZING - preserves exact image quality")
            print("  • Shows folder contents first")
            print("  • You select image by number")
            print("  • Choose JPEG quality (1-100)")
            print("  • Warns about large file transmission times")
            print("  • Perfect for research requiring original quality")
            print("Process:")
            print("  1. Scans folder and shows images")
            print("  2. You enter image number")
            print("  3. You set quality (85-100 recommended)")
            print("  4. Shows transmission time estimate")
            print("  5. Asks for confirmation before sending")
            print("Warning:")
            print("  • Large images take 30+ minutes to transmit")
            print("  • 4K images can take 2+ hours")
        
        elif command == 'batch':
            print("\n🔄 BATCH COMMAND")
            print("-" * 30)
            print("Purpose: Send multiple images sequentially")
            print("Usage: batch")
            print("Description:")
            print("  • Send range of images automatically")
            print("  • Choose start and end image numbers")
            print("  • Select quality and resolution mode")
            print("  • 5-second delay between images")
            print("  • Shows progress for each image")
            print("Process:")
            print("  1. Scans folder and shows all images")
            print("  2. You enter start image number")
            print("  3. You enter end image number")
            print("  4. Choose quality (1-100)")
            print("  5. Choose original or resized mode")
            print("  6. Confirms settings before starting")
            print("  7. Sends images one by one")
            print("Example:")
            print("  Start: 0, End: 4 = sends images 0,1,2,3,4")
            print("  Useful for sending test sequences")
        
        elif command == 'batch':
            print("\n🔄 BATCH COMMAND")
            print("-" * 30)
            print("Purpose: Send multiple images sequentially")
            print("Usage: batch")
            print("Description:")
            print("  • Send range of images automatically")
            print("  • Choose start and end image numbers")
            print("  • Select quality and resolution mode")
            print("  • 5-second delay between images")
            print("  • Shows progress for each image")
            print("Process:")
            print("  1. Scans folder and shows all images")
            print("  2. You enter start image number")
            print("  3. You enter end image number")
            print("  4. Choose quality (1-100)")
            print("  5. Choose original or resized mode")
            print("  6. Confirms settings before starting")
            print("  7. Sends images one by one")
            print("Example:")
            print("  Start: 0, End: 4 = sends images 0,1,2,3,4")
            print("  Useful for sending test sequences")
        
        elif command == 'test':
            print("\n🧪 TEST COMMAND")
            print("-" * 30)
            print("Purpose: Send simple text strings to test LoRa connection")
            print("Usage: test")
            print("Description:")
            print("  • Quick way to verify TX-RX communication")
            print("  • Send custom text messages")
            print("  • No camera or image processing required")
            print("  • Instant transmission (no fragmentation)")
            print("  • Perfect for initial setup verification")
            print("Process:")
            print("  1. You enter any text message")
            print("  2. Message is sent immediately via LoRa")
            print("  3. RX should receive and display the message")
            print("Examples:")
            print("  'Hello World' - Basic connectivity test")
            print("  'TX1 Ready' - Node identification")
            print("  'Test 123' - Simple test message")
            print("Use this before sending images to ensure connection works!")
        
        elif command == 'send-folder-image':
            print("\n📁 SEND-FOLDER-IMAGE COMMAND")
            print("-" * 30)
            print("Purpose: Send specific image from folder by number")
            print("Usage: send-folder-image <image_number>")
            print("Description:")
            print("  • Quick way to send images using scan results")
            print("  • Reference images by their scan number")
            print("  • Uses optimized settings for reliable transmission")
            print("  • Automatically handles size validation")
            print("Process:")
            print("  1. First run 'scan' to see numbered image list")
            print("  2. Use 'send-folder-image <number>' to send specific image")
            print("  3. System applies smart compression and validation")
            print("  4. Sends image with progress tracking")
            print("Examples:")
            print("  send-folder-image 0    # Send first image from scan")
            print("  send-folder-image 3    # Send fourth image from scan")
            print("Note:")
            print("  • Always run 'scan' first to see available images")
            print("  • Uses balanced quality (70%) for reliable transmission")
            print("  • Auto-resizes if image exceeds size limits")
        
        else:
            print(f"❌ No help available for '{command}'")
            print("Available help topics: folder, scan, original, batch, test, send-folder-image")
    
    def load_image_file_original(self, file_path, quality=85):
        """
        Load an existing image file at ORIGINAL resolution for LoRa transmission
        NO RESIZING - sends exactly as captured
        
        Args:
            file_path: Path to the image file
            quality: JPEG quality for compression only (1-100)
        """
        if not os.path.exists(file_path):
            raise Exception(f"Image file not found: {file_path}")
        
        # Load image
        image = cv2.imread(file_path)
        if image is None:
            raise Exception(f"Could not load image: {file_path}")
        
        original_size = (image.shape[1], image.shape[0])
        print(f"📂 Loaded: {os.path.basename(file_path)}")
        print(f"📏 ORIGINAL Resolution: {original_size[0]}x{original_size[1]} pixels")
        print(f"🎯 NO RESIZING - Sending at full resolution")
        
        # Encode to JPEG at specified quality - NO RESIZING
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ret, buffer = cv2.imencode('.jpg', image, encode_param)
        
        if not ret:
            raise Exception("Failed to encode image")
        
        final_size = len(buffer)
        print(f"📦 Final size: {final_size:,} bytes (quality: {quality}%)")
        
        # Calculate realistic transmission estimates
        estimated_fragments = (final_size + 165) // 165
        estimated_time = estimated_fragments * 1.8
        
        print(f"⏱️  Estimated transmission: ~{estimated_time/60:.1f} minutes ({estimated_fragments} fragments)")
        print(f"📊 Data rate: ~{(final_size*8)/(estimated_time*1000):.2f} Kbps")
        
    def load_image_file(self, file_path, quality=60, target_size=None):
        """
        Load an existing image file and prepare it for LoRa transmission
        
        Args:
            file_path: Path to the image file
            quality: JPEG quality for compression (1-100)
            target_size: Target resolution tuple (width, height) or None for auto
        """
        if not os.path.exists(file_path):
            raise Exception(f"Image file not found: {file_path}")
        
        # Load image
        image = cv2.imread(file_path)
        if image is None:
            raise Exception(f"Could not load image: {file_path}")
        
        original_size = (image.shape[1], image.shape[0])
        print(f"📂 Loaded image: {os.path.basename(file_path)} ({original_size[0]}x{original_size[1]})")
        
        # Apply resizing logic (same as capture_image)
        if target_size:
            image_resized = cv2.resize(image, target_size)
            print(f"📏 Resized to: {target_size[0]}x{target_size[1]}")
        else:
            # Auto-optimization
            target_pixels = 320 * 240
            current_pixels = original_size[0] * original_size[1]
            
            if current_pixels > target_pixels:
                scale = (target_pixels / current_pixels) ** 0.5
                new_width = int(original_size[0] * scale)
                new_height = int(original_size[1] * scale)
                new_width = new_width - (new_width % 2)
                new_height = new_height - (new_height % 2)
                image_resized = cv2.resize(image, (new_width, new_height))
                print(f"📏 Auto-resized to: {new_width}x{new_height} (scale: {scale:.2f})")
            else:
                image_resized = image
                print(f"📏 Keeping original size: {original_size[0]}x{original_size[1]}")
        
        # Encode to JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ret, buffer = cv2.imencode('.jpg', image_resized, encode_param)
        
        if not ret:
            raise Exception("Failed to encode image")
        
        final_size = len(buffer)
        print(f"📦 Final size: {final_size} bytes (quality: {quality}%)")
        
        # Estimate transmission time
        estimated_fragments = (final_size + 165) // 165
        estimated_time = estimated_fragments * 1.8
        print(f"⏱️  Estimated transmission: ~{estimated_time:.1f}s ({estimated_fragments} fragments)")
        
        return buffer.tobytes()
    
    def scan_image_folder(self, folder_path=None):
        """
        Scan specified folder for images and return detailed information
        
        Args:
            folder_path: Custom folder path, or None to use default
        """
        if folder_path is None:
            folder_path = self.image_folder
        
        if not os.path.exists(folder_path):
            print(f"📁 Folder '{folder_path}' not found!")
            create_folder = input(f"Create folder '{folder_path}'? (y/n): ").lower().strip()
            if create_folder == 'y':
                os.makedirs(folder_path, exist_ok=True)
                print(f"✅ Created folder: {folder_path}")
                return []
            else:
                return []
        
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']
        image_files = []
        
        print(f"🔍 Scanning folder: {os.path.abspath(folder_path)}")
        
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(folder_path, ext)))
            image_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))
        
        # Remove duplicates and sort
        image_files = sorted(list(set(image_files)))
        
        print(f"📊 Found {len(image_files)} images in folder")
        
        if not image_files:
            print(f"💡 No images found. Supported formats: JPG, PNG, BMP, TIFF")
            print(f"💡 Copy some images to '{folder_path}' to get started")
            return []
        
        print(f"\n📋 Image Details:")
        print("-" * 80)
        
        total_size = 0
        for i, file_path in enumerate(image_files):
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            
            # Get image dimensions
            try:
                temp_img = cv2.imread(file_path)
                if temp_img is not None:
                    height, width = temp_img.shape[:2]
                    dimensions = f"{width}x{height}"
                    megapixels = (width * height) / 1000000
                else:
                    dimensions = "Unknown"
                    megapixels = 0
            except:
                dimensions = "Error"
                megapixels = 0
            
            print(f"{i:2d}: {filename:<25} {file_size/1024:8.1f}KB  {dimensions:>10}  {megapixels:.1f}MP")
        
        print("-" * 80)
        print(f"📊 Total: {len(image_files)} images, {total_size/1024/1024:.1f}MB")
        
        # Estimate total transmission time
        if len(image_files) > 0:
            avg_size = total_size / len(image_files)
            est_time_per_image = (avg_size * 8) / (165 * 1.8 * 1000)  # Rough estimate
            total_est_time = est_time_per_image * len(image_files)
            print(f"⏱️  Estimated total transmission time: ~{total_est_time/60:.1f} minutes")
        
        return image_files
    
    def list_available_images(self):
        """List all available images in the test folder"""
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(self.image_folder, ext)))
            image_files.extend(glob.glob(os.path.join(self.image_folder, ext.upper())))
        
        if not image_files:
            print(f"📁 No images found in '{self.image_folder}' folder")
            print(f"💡 Copy some images to the '{self.image_folder}' folder to use this feature")
            return []
        
        print(f"📁 Available images in '{self.image_folder}':")
        for i, file_path in enumerate(image_files):
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            print(f"   {i}: {filename} ({file_size} bytes)")
        
        return image_files
    
    def save_captured_image(self, image_data, filename=None):
        """Save a captured image to the test folder for later use"""
        if filename is None:
            filename = f"captured_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        filepath = os.path.join(self.image_folder, filename)
        
        # Convert bytes back to image and save
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if image is not None:
            cv2.imwrite(filepath, image)
            print(f"💾 Image saved to: {filepath}")
            return filepath
        else:
            print(f"❌ Failed to save image")
            return None
    
    def send_rak_packet(self, data_hex):
        """Send a single packet via RAK3172 with enhanced error handling"""
        try:
            # Send packet using AT+PSEND
            cmd = f"AT+PSEND={data_hex}\r\n"
            self.connection.write(cmd.encode())
            time.sleep(1.5)  # Wait for transmission
            
            # Check response
            response = ""
            if self.connection.in_waiting:
                response = self.connection.read_all().decode().strip()
            
            # Enhanced success checking
            if "+EVT:TXP2P" in response:
                return True  # Confirmed transmission
            elif "OK" in response:
                return True  # AT command accepted
            elif response == "":
                return True  # No response often means success
            elif "AT_BUSY_ERROR" in response:
                print("⚠️  Module busy, retrying...")
                time.sleep(2)
                # Retry once
                self.connection.write(cmd.encode())
                time.sleep(1.5)
                retry_response = ""
                if self.connection.in_waiting:
                    retry_response = self.connection.read_all().decode().strip()
                return "+EVT:TXP2P" in retry_response or "OK" in retry_response
            else:
                print(f"⚠️  Unexpected response: {response}")
                return False
            
        except Exception as e:
            print(f"❌ Send packet error: {e}")
            return False
    
    def fragment_data(self, data, max_payload=180):
        """Fragment image data for LoRa transmission - SUPPORTS LARGE IMAGES"""
        # Reserve space for packet header
        header_size = 15  # packet_type(1) + image_id(8) + fragment_info(6)
        chunk_size = max_payload - header_size
        
        fragments = []
        total_fragments = (len(data) + chunk_size - 1) // chunk_size
        
        # Now supports much larger images - only limited by available memory
        if total_fragments > 1000000:  # 1 million fragments (very conservative limit)
            print(f"⚠️  Warning: Extremely large image ({total_fragments:,} fragments)")
            print(f"   This would take approximately {(total_fragments * 1.8)/3600:.1f} hours to transmit")
            print(f"   Consider reducing image size or quality")
            raise Exception(f"Image too large: {total_fragments:,} fragments would take too long to transmit")
        
        print(f"📊 Image fragmentation: {len(data):,} bytes → {total_fragments:,} fragments")
        
        for i in range(0, len(data), chunk_size):
            fragment_id = i // chunk_size
            chunk = data[i:i + chunk_size]
            fragments.append((fragment_id, chunk))
        
        return fragments, total_fragments
    
    def send_image(self, image_data, image_id):
        """Send complete image via LoRa"""
        print(f"📤 Starting transmission of '{image_id}' ({len(image_data)} bytes)")
        
        # Fragment the image
        fragments, total_fragments = self.fragment_data(image_data)
        transmission_start = time.time()
        
        # Send start packet
        print(f"📡 Sending start packet...")
        start_time_bytes = struct.pack('<d', transmission_start)
        image_id_bytes = image_id.encode('utf-8')[:8].ljust(8, b'\x00')
        
        start_packet = (b'S' + image_id_bytes + 
                       struct.pack('<HH', len(image_data), total_fragments) + 
                       start_time_bytes)
        start_hex = start_packet.hex().upper()
        
        if not self.send_rak_packet(start_hex):
            print("❌ Failed to send start packet")
            print("💡 Possible causes:")
            print("   • LoRa connection lost")
            print("   • Module not responding")
            print("   • Check COM port connection")
            return None
        
        time.sleep(0.5)
        
        # Send fragments
        successful_fragments = 0
        for fragment_id, chunk in fragments:
            packet = (b'F' + image_id_bytes + 
                     struct.pack('<HHH', fragment_id, total_fragments, len(chunk)) + 
                     chunk)
            packet_hex = packet.hex().upper()
            
            print(f"📡 Sending fragment {fragment_id + 1:2d}/{total_fragments} ({len(chunk):3d} bytes)", end="")
            
            if self.send_rak_packet(packet_hex):
                successful_fragments += 1
                print(" ✅")
            else:
                print(" ❌")
            
            time.sleep(0.3)  # Brief pause between fragments
        
        # Send end packet
        transmission_end = time.time()
        end_time_bytes = struct.pack('<d', transmission_end)
        end_packet = b'E' + image_id_bytes + end_time_bytes
        end_hex = end_packet.hex().upper()
        
        print(f"📡 Sending end packet...")
        if not self.send_rak_packet(end_hex):
            print("❌ Failed to send end packet")
            print("⚠️  Image data was transmitted but end marker failed")
            print("💡 Receiver may still reconstruct the image")
        
        # Calculate results
        duration = transmission_end - transmission_start
        success_rate = (successful_fragments / total_fragments) * 100
        
        # Log transmission
        record = {
            'image_id': image_id,
            'start_time': transmission_start,
            'end_time': transmission_end,
            'duration': duration,
            'image_size': len(image_data),
            'total_fragments': total_fragments,
            'successful_fragments': successful_fragments,
            'success_rate': success_rate,
            'timestamp': datetime.now().isoformat()
        }
        
        self.transmission_log.append(record)
        
        print(f"✅ Transmission completed!")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Fragments sent: {successful_fragments}/{total_fragments}")
        
        return record
    
    def print_statistics(self):
        """Print transmission statistics"""
        if not self.transmission_log:
            print("📊 No transmissions yet")
            return
        
        total_tx = len(self.transmission_log)
        avg_duration = sum(r['duration'] for r in self.transmission_log) / total_tx
        avg_success = sum(r['success_rate'] for r in self.transmission_log) / total_tx
        total_size = sum(r['image_size'] for r in self.transmission_log)
        total_time = sum(r['duration'] for r in self.transmission_log)
        
        print(f"\n📊 Transmission Statistics:")
        print(f"   Total images sent: {total_tx}")
        print(f"   Average duration: {avg_duration:.2f}s")
        print(f"   Average success rate: {avg_success:.1f}%")
        print(f"   Total data sent: {total_size/1024:.1f} KB")
        print(f"   Average throughput: {(total_size*8)/(total_time*1000):.2f} Kbps")
    
    def cleanup(self):
        """Clean up resources"""
        if self.camera:
            self.camera.release()
        if self.connection:
            self.connection.close()


def main():
    """Main transmitter application"""
    print("📤 RAK3172 LoRa Image Transmitter")
    print("=" * 50)
    
    # Get configuration
    port = input("Enter Transmitter COM port (e.g., COM10): ")
    
    # Ask about operation mode
    print("\n🎯 Choose operation mode:")
    print("1. Send pre-captured images from folder (no camera needed)")
    print("2. Capture new images with camera and send")
    
    mode = input("Enter choice (1 or 2, default=1): ").strip()
    need_camera = (mode == "2")
    
    camera_index = 0
    if need_camera:
        try:
            camera_choice = input("Enter camera index (0=built-in, 1=USB, default=0): ").strip()
            if camera_choice:
                camera_index = int(camera_choice)
        except ValueError:
            camera_index = 0
    
    # Initialize transmitter
    transmitter = RAK3172ImageTransmitter(port, camera_index=camera_index)
    
    if not transmitter.initialize_hardware(init_camera=need_camera):
        print("❌ Failed to initialize transmitter")
        return
    
    print(f"\n🚀 Transmitter ready!")
    print("Commands:")
    print("  help          - Show all commands")
    print("  help <cmd>    - Show detailed help for specific command")
    print("  test          - Send text string to test LoRa connection")
    print("  folder        - Set custom image folder path")
    print("  scan          - Scan and analyze images in current folder")
    print("  send-folder-image - Send specific image by number (e.g., send-folder-image 0)")
    print("  original      - Send image at ORIGINAL resolution")
    print("  batch         - Send multiple images sequentially")
    if need_camera:
        print("  send          - Capture and send from camera")
        print("  capture       - Capture image and save to folder")
    print("  stats         - Show transmission statistics")
    print("  quit          - Exit")
    
    try:
        while True:
            command = input(f"\nTransmitter> ").strip().lower()
            
            if command == 'quit':
                break
            
            elif command == 'help':
                transmitter.print_help()
                
            elif command.startswith('help '):
                help_cmd = command.split(' ', 1)[1]
                transmitter.print_help(help_cmd)
                
            elif command == 'test':
                try:
                    print("🧪 LoRa Connection Test Mode")
                    print("Send simple text messages to verify TX-RX communication")
                    print("Type 'back' to return to main menu")
                    
                    while True:
                        message = input("Test message> ").strip()
                        
                        if message.lower() == 'back':
                            break
                        elif message:
                            success = transmitter.send_test_string(message)
                            if success:
                                print("💡 Check receiver for the message!")
                            else:
                                print("❌ Test failed - check LoRa connection")
                        else:
                            print("💡 Enter a message or 'back' to exit test mode")
                    
                except Exception as e:
                    print(f"❌ Test error: {e}")
            
            elif command == 'folder':
                try:
                    current_folder = transmitter.image_folder
                    print(f"📁 Current image folder: {os.path.abspath(current_folder)}")
                    
                    new_folder = input("Enter new folder path (or press Enter to keep current): ").strip()
                    if new_folder:
                        transmitter.image_folder = new_folder
                        print(f"✅ Image folder changed to: {os.path.abspath(new_folder)}")
                        
                        # Scan the new folder
                        transmitter.scan_image_folder()
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command.startswith('send-folder-image'):
                try:
                    # Parse command: "send-folder-image 0" or "send-folder-image"
                    parts = command.split()
                    
                    if len(parts) == 1:
                        # No number provided, show usage
                        print("📁 Send-Folder-Image Command")
                        print("Usage: send-folder-image <image_number>")
                        print("First run 'scan' to see numbered images, then use:")
                        print("  send-folder-image 0    # Send first image")
                        print("  send-folder-image 3    # Send fourth image")
                        continue
                    
                    try:
                        image_number = int(parts[1])
                    except ValueError:
                        print("❌ Invalid image number. Use: send-folder-image <number>")
                        continue
                    
                    # Get current image list
                    image_files = transmitter.scan_image_folder()
                    if not image_files:
                        print("❌ No images found. Use 'folder' to set image directory.")
                        continue
                    
                    if image_number < 0 or image_number >= len(image_files):
                        print(f"❌ Image number {image_number} out of range (0-{len(image_files)-1})")
                        print("💡 Run 'scan' to see available images")
                        continue
                    
                    selected_file = image_files[image_number]
                    filename = os.path.basename(selected_file)
                    
                    print(f"📂 Sending image {image_number}: {filename}")
                    
                    # Use smart loading with size validation
                    try:
                        # Try with balanced quality first
                        image_data = transmitter.load_image_file(selected_file, quality=70)
                        
                        # Check size and adjust if needed
                        if len(image_data) > 65535:
                            print("⚠️  Image too large, reducing quality...")
                            image_data = transmitter.load_image_file(selected_file, quality=50)
                            
                            if len(image_data) > 65535:
                                print("⚠️  Still too large, applying auto-resize...")
                                # Use even more aggressive compression
                                image_data = transmitter.load_image_file(selected_file, quality=30, target_size=(240, 180))
                        
                        image_id = f"folder_{image_number}_{datetime.now().strftime('%H%M%S')}"
                        transmitter.send_image(image_data, image_id)
                        
                    except Exception as size_error:
                        print(f"❌ Error processing image: {size_error}")
                        print("💡 Try using 'original' command with lower quality settings")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command == 'send' and need_camera:
                try:
                    print("📸 Capturing optimized image...")
                    image_data = transmitter.capture_image(quality=60)  # Balanced quality
                    
                    image_id = f"opt_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command == 'capture' and need_camera:
                try:
                    print("📸 Capturing image to save...")
                    image_data = transmitter.capture_image(quality=70)  # Higher quality for storage
                    
                    filename = input("Enter filename (or press Enter for auto): ").strip()
                    if not filename:
                        filename = None
                    elif not filename.lower().endswith(('.jpg', '.jpeg')):
                        filename += '.jpg'
                    
                    saved_path = transmitter.save_captured_image(image_data, filename)
                    if saved_path:
                        print(f"✅ Image captured and saved. Use 'original' command to send it later.")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command in ['send', 'capture'] and not need_camera:
                print("❌ Camera commands not available in folder-only mode")
                print("💡 Restart and choose option 2 to enable camera features")
            
            elif command == 'scan':
                try:
                    transmitter.scan_image_folder()
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command == 'original':
                try:
                    image_files = transmitter.scan_image_folder()
                    if not image_files:
                        continue
                    
                    print(f"\n🎯 ORIGINAL RESOLUTION MODE - No resizing will be applied")
                    
                    # Get user selection
                    try:
                        choice = int(input("Enter image number to send at ORIGINAL resolution: "))
                        if 0 <= choice < len(image_files):
                            selected_file = image_files[choice]
                            filename = os.path.basename(selected_file)
                            
                            # Get quality setting
                            quality = input("Enter JPEG quality 1-100 (default 85): ").strip()
                            quality = int(quality) if quality else 85
                            
                            print(f"\n📂 Preparing {filename} at ORIGINAL resolution...")
                            
                            # Confirm before sending (large images take time)
                            confirm = input("This may take a long time for large images. Continue? (y/n): ").lower().strip()
                            if confirm != 'y':
                                print("❌ Transmission cancelled")
                                continue
                            
                            image_data = transmitter.load_image_file_original(selected_file, quality)
                            
                            image_id = f"orig_{datetime.now().strftime('%H%M%S')}"
                            transmitter.send_image(image_data, image_id)
                            
                        else:
                            print("❌ Invalid selection")
                    except ValueError:
                        print("❌ Please enter a valid number")
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command == 'batch':
                try:
                    image_files = transmitter.scan_image_folder()
                    if not image_files:
                        continue
                    
                    print(f"\n🔄 BATCH TRANSMISSION MODE")
                    
                    # Get range of images to send
                    start_idx = input(f"Enter start image number (0-{len(image_files)-1}, default 0): ").strip()
                    start_idx = int(start_idx) if start_idx else 0
                    
                    end_idx = input(f"Enter end image number (0-{len(image_files)-1}, default {len(image_files)-1}): ").strip()
                    end_idx = int(end_idx) if end_idx else len(image_files)-1
                    
                    if start_idx < 0 or end_idx >= len(image_files) or start_idx > end_idx:
                        print("❌ Invalid range")
                        continue
                    
                    # Get quality and mode
                    quality = input("Enter JPEG quality 1-100 (default 85): ").strip()
                    quality = int(quality) if quality else 85
                    
                    mode = input("Send at (o)riginal resolution or (r)esized? (o/r, default o): ").lower().strip()
                    original_mode = mode != 'r'
                    
                    selected_images = image_files[start_idx:end_idx+1]
                    print(f"\n🚀 Will send {len(selected_images)} images from index {start_idx} to {end_idx}")
                    print(f"   Mode: {'ORIGINAL resolution' if original_mode else 'Auto-resized'}")
                    print(f"   Quality: {quality}%")
                    
                    confirm = input("Start batch transmission? (y/n): ").lower().strip()
                    if confirm != 'y':
                        print("❌ Batch transmission cancelled")
                        continue
                    
                    # Send images one by one
                    for i, file_path in enumerate(selected_images):
                        filename = os.path.basename(file_path)
                        print(f"\n📤 Batch {i+1}/{len(selected_images)}: {filename}")
                        
                        try:
                            # Load image data
                            if original_mode:
                                image_data = transmitter.load_image_file_original(file_path, quality)
                            else:
                                image_data = transmitter.load_image_file(file_path, quality)
                            
                            print(f"📊 Image size: {len(image_data):,} bytes")
                            
                            # For very large images, show estimated time and ask for confirmation
                            estimated_fragments = (len(image_data) + 165) // 165
                            estimated_minutes = (estimated_fragments * 1.8) / 60
                            
                            if estimated_minutes > 20:
                                print(f"⏱️  Estimated transmission: ~{estimated_minutes:.1f} minutes")
                                print(f"📊 This is a large image with {estimated_fragments:,} fragments")
                                
                                continue_choice = input(f"Proceed with this large transmission? (y/n): ").lower().strip()
                                if continue_choice != 'y':
                                    print(f"⏭️  Skipping {filename}")
                                    continue
                            
                            # Check LoRa connection before transmission
                            print("🔍 Testing LoRa connection...")
                            test_success = transmitter.send_test_string("BATCH_TEST")
                            if not test_success:
                                print("❌ LoRa connection test failed!")
                                print("💡 Possible issues:")
                                print("   • Module disconnected")
                                print("   • COM port error")
                                print("   • Module in wrong mode")
                                
                                retry_choice = input("Try to reconnect and continue? (y/n): ").lower().strip()
                                if retry_choice == 'y':
                                    # Try to reinitialize LoRa
                                    try:
                                        transmitter.setup_rak3172_transmitter()
                                        print("✅ LoRa reinitialized")
                                    except Exception as reinit_error:
                                        print(f"❌ Reinitialize failed: {reinit_error}")
                                        print("🛑 Stopping batch transmission")
                                        break
                                else:
                                    print("🛑 Batch transmission stopped")
                                    break
                            
                            # Attempt transmission
                            image_id = f"batch_{i:02d}_{datetime.now().strftime('%H%M%S')}"
                            print(f"📡 Starting transmission of {image_id}...")
                            
                            tx_record = transmitter.send_image(image_data, image_id)
                            
                            # Check if transmission was successful
                            if tx_record is not None:
                                print(f"✅ Batch {i+1} completed successfully")
                                print(f"   Duration: {tx_record.get('duration', 0)/60:.1f} minutes")
                                print(f"   Success rate: {tx_record.get('success_rate', 0):.1f}%")
                                print(f"   Throughput: {(tx_record.get('image_size', 0)*8)/(tx_record.get('duration', 1)*1000):.2f} Kbps")
                            else:
                                print(f"❌ Batch {i+1} failed - transmission returned None")
                                print("🔍 Debugging information:")
                                print(f"   • Image loaded successfully: {len(image_data):,} bytes")
                                print(f"   • LoRa connection status: Unknown (check COM port)")
                                print(f"   • Likely cause: Start packet transmission failed")
                                
                                debug_choice = input("Try to debug LoRa connection? (y/n): ").lower().strip()
                                if debug_choice == 'y':
                                    print("🧪 Running LoRa diagnostics...")
                                    
                                    # Test basic AT commands
                                    try:
                                        transmitter.connection.write(b"AT\r\n")
                                        time.sleep(1)
                                        response = transmitter.connection.read_all().decode().strip()
                                        if "OK" in response:
                                            print("✅ Basic AT command working")
                                        else:
                                            print(f"❌ AT command failed: {response}")
                                    except Exception as at_error:
                                        print(f"❌ AT command error: {at_error}")
                                    
                                    # Test simple send
                                    test_result = transmitter.send_test_string("DEBUG_TEST")
                                    if test_result:
                                        print("✅ Simple send working")
                                    else:
                                        print("❌ Simple send failed")
                                
                                continue_choice = input("Continue with remaining images? (y/n): ").lower().strip()
                                if continue_choice != 'y':
                                    print("🛑 Batch transmission stopped")
                                    break
                            
                            if i < len(selected_images) - 1:  # Don't wait after last image
                                print("⏳ Waiting 5 seconds before next image...")
                                time.sleep(5)
                        
                        except Exception as e:
                            print(f"❌ Error with {filename}: {e}")
                            print(f"💡 Possible causes:")
                            print(f"   • LoRa connection issue")
                            print(f"   • File corruption")
                            print(f"   • Image format not supported")
                            print(f"   • Transmission interrupted")
                            
                            continue_batch = input("Continue with remaining images? (y/n): ").lower().strip()
                            if continue_batch != 'y':
                                print("🛑 Batch transmission stopped")
                                break
                    
                    print(f"✅ Batch transmission completed!")
                    
                except ValueError:
                    print("❌ Invalid input")
                except Exception as e:
                    print(f"❌ Error: {e}")
                
            elif command == 'file':
                try:
                    image_files = transmitter.list_available_images()
                    if not image_files:
                        continue
                    
                    # Get user selection
                    try:
                        choice = int(input("Enter image number to send: "))
                        if 0 <= choice < len(image_files):
                            selected_file = image_files[choice]
                            filename = os.path.basename(selected_file)
                            
                            print(f"📂 Loading {filename}...")
                            image_data = transmitter.load_image_file(selected_file, quality=60)
                            
                            image_id = f"file_{datetime.now().strftime('%H%M%S')}"
                            transmitter.send_image(image_data, image_id)
                            
                        else:
                            print("❌ Invalid selection")
                    except ValueError:
                        print("❌ Please enter a valid number")
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command == 'send':
                try:
                    print("📸 Capturing optimized image...")
                    image_data = transmitter.capture_image(quality=60)  # Balanced quality
                    
                    image_id = f"opt_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command == 'list':
                transmitter.list_available_images()
                
            elif command == 'capture':
                try:
                    print("📸 Capturing image to save...")
                    image_data = transmitter.capture_image(quality=70)  # Higher quality for storage
                    
                    filename = input("Enter filename (or press Enter for auto): ").strip()
                    if not filename:
                        filename = None
                    elif not filename.lower().endswith(('.jpg', '.jpeg')):
                        filename += '.jpg'
                    
                    saved_path = transmitter.save_captured_image(image_data, filename)
                    if saved_path:
                        print(f"✅ Image captured and saved. Use 'file' command to send it later.")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                try:
                    print("📸 Capturing optimized image...")
                    image_data = transmitter.capture_image(quality=60)  # Balanced quality
                    
                    image_id = f"opt_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command == 'hq':
                try:
                    print("📸 Capturing HIGH QUALITY image...")
                    image_data = transmitter.capture_image(quality=80, target_size=(480, 360))
                    
                    image_id = f"hq_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command == 'fast':
                try:
                    print("📸 Capturing FAST image...")
                    image_data = transmitter.capture_image(quality=40, target_size=(240, 180))
                    
                    image_id = f"fast_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command == 'custom':
                try:
                    print("📸 Custom image capture...")
                    
                    # Get custom parameters
                    width = int(input("Enter width (e.g., 320): ") or "320")
                    height = int(input("Enter height (e.g., 240): ") or "240")
                    quality = int(input("Enter quality 1-100 (e.g., 70): ") or "70")
                    
                    print(f"📸 Capturing custom image: {width}x{height} at {quality}% quality...")
                    image_data = transmitter.capture_image(quality=quality, target_size=(width, height))
                    
                    image_id = f"custom_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except ValueError:
                    print("❌ Invalid input. Please enter numbers only.")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command == 'test':
                try:
                    print("📸 Capturing test image...")
                    image_data = transmitter.capture_image(quality=50, target_size=(160, 120))
                    
                    image_id = f"test_{datetime.now().strftime('%H%M%S')}"
                    transmitter.send_image(image_data, image_id)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command.startswith('auto'):
                try:
                    parts = command.split()
                    num_images = int(parts[1]) if len(parts) > 1 else 3
                    
                    print(f"🔄 Sending {num_images} images automatically...")
                    
                    for i in range(num_images):
                        try:
                            print(f"\n📸 Image {i+1}/{num_images}")
                            # Use balanced settings for auto mode
                            image_data = transmitter.capture_image(quality=55)
                            image_id = f"auto_{i:02d}_{datetime.now().strftime('%H%M%S')}"
                            
                            transmitter.send_image(image_data, image_id)
                            
                            if i < num_images - 1:  # Don't wait after last image
                                print("⏳ Waiting 3 seconds before next image...")
                                time.sleep(3)
                            
                        except Exception as e:
                            print(f"❌ Error with image {i+1}: {e}")
                    
                    print(f"✅ Auto transmission sequence complete!")
                    
                except ValueError:
                    print("❌ Invalid number. Usage: auto <number>")
                except Exception as e:
                    print(f"❌ Auto transmission error: {e}")
            
            elif command == 'stats':
                transmitter.print_statistics()
            
            else:
                print("❌ Unknown command.")
                print("💡 Type 'help' to see all available commands")
        
    except KeyboardInterrupt:
        print("\n🛑 Transmitter stopped by user")
    
    finally:
        transmitter.print_statistics()
        transmitter.cleanup()
        print("✅ Transmitter cleanup completed")


if __name__ == "__main__":
    main()