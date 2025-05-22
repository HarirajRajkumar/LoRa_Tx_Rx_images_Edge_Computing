#!/usr/bin/env python3
"""
Dedicated LoRa Image Receiver for RAK3172
Run this script on the receiving device
"""

import serial
import time
import struct
import numpy as np
import cv2
import threading
import queue
from datetime import datetime
import os

class RAK3172ImageReceiver:
    """
    Dedicated receiver for RAK3172 LoRa image transmission
    """
    def __init__(self, serial_port, baud_rate=115200):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.connection = None
        self.running = False
        self.current_images = {}
        self.completed_images = []
        self.image_save_dir = "received_images"
        
        # Create directory for saving images
        os.makedirs(self.image_save_dir, exist_ok=True)
        
    def initialize_hardware(self):
        """Initialize LoRa connection and setup RAK3172"""
        try:
            self.connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            print("🔧 Setting up RAK3172 for receiving...")
            self.setup_rak3172_receiver()
            
            print(f"✅ Receiver initialized: {self.serial_port} at {self.baud_rate} baud")
            return True
            
        except Exception as e:
            print(f"❌ Receiver initialization failed: {e}")
            return False
    
    def setup_rak3172_receiver(self):
        """Setup RAK3172 specifically for receiving"""
        # First, stop any existing RX mode
        print("Stopping any existing P2P RX mode...")
        self.connection.write(b"AT+PRECV=0\r\n")
        time.sleep(1)
        response = self.connection.read_all().decode().strip()
        print(f"Stop RX: {response}")
        
        # Configure P2P parameters
        setup_commands = [
            ("AT+NWM=0", "Set to LoRa P2P mode"),
            ("AT+PFREQ=868000000", "Set frequency to 868MHz"),
            ("AT+PSF=7", "Set spreading factor to 7"),
            ("AT+PBW=125", "Set bandwidth to 125kHz"),
            ("AT+PCR=1", "Set coding rate to 4/5"),
            ("AT+PPL=8", "Set preamble length to 8"),
            ("AT+PTP=20", "Set TX power to 20dBm"),
        ]
        
        for cmd, description in setup_commands:
            print(f"Setting: {description}")
            self.connection.write(f"{cmd}\r\n".encode())
            time.sleep(1)
            response = self.connection.read_all().decode().strip()
            
            if "OK" in response or response == "":
                print(f"✅ {description}")
            else:
                print(f"⚠️  {description}: {response}")
        
        # Enable continuous P2P receive mode
        print("Enabling continuous P2P receive mode...")
        self.connection.write(b"AT+PRECV=65534\r\n")
        time.sleep(1)
        response = self.connection.read_all().decode().strip()
        print(f"✅ P2P RX enabled: {response}")
    
    def start_listening(self):
        """Start listening for incoming image transmissions"""
        self.running = True
        print("📡 Starting LoRa image receiver...")
        print("🎯 Waiting for incoming image transmissions...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                if self.connection.in_waiting > 0:
                    line = self.connection.readline().decode().strip()
                    
                    # Process RAK3172 P2P receive messages
                    if "+EVT:RXP2P:" in line:
                        self._process_received_message(line)
                    elif line.strip():
                        print(f"ℹ️  Module: {line}")
                
                time.sleep(0.01)  # Small delay to prevent busy waiting
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping receiver...")
            self.running = False
        except Exception as e:
            print(f"❌ Listening error: {e}")
    
    def _process_received_message(self, line):
        """Process received RAK3172 P2P message"""
        try:
            # Parse: +EVT:RXP2P:RSSI:SNR:HexData
            parts = line.split(":")
            if len(parts) >= 4:
                rssi = parts[2]
                snr = parts[3]
                hex_data = ":".join(parts[4:]) if len(parts) > 4 else ""
                
                # Convert hex to bytes
                if hex_data:
                    try:
                        clean_hex = ''.join(c for c in hex_data if c in '0123456789ABCDEFabcdef')
                        if len(clean_hex) % 2 == 0 and len(clean_hex) > 0:
                            packet_data = bytes.fromhex(clean_hex)
                            
                            # Check if this is image data or simple text
                            if len(packet_data) > 0 and packet_data[0:1] in [b'S', b'F', b'E']:
                                # This is image packet data (starts with S, F, or E)
                                self._handle_image_packet(packet_data, rssi, snr)
                            else:
                                # This is a simple text message
                                try:
                                    text_message = packet_data.decode('utf-8')
                                    timestamp = datetime.now().strftime('%H:%M:%S')
                                    print(f"💬 [{timestamp}] Text Message: '{text_message}' (RSSI={rssi}dBm, SNR={snr}dB)")
                                except UnicodeDecodeError:
                                    # Not valid text, show as raw data
                                    print(f"📨 [{timestamp}] Data received: {len(packet_data)} bytes (RSSI={rssi}dBm, SNR={snr}dB)")
                    except Exception as e:
                        print(f"⚠️  Hex decode error: {e}")
                
        except Exception as e:
            print(f"❌ Message processing error: {e}")
    
    def _handle_image_packet(self, packet_data, rssi, snr):
        """Handle different types of image packets"""
        if len(packet_data) < 1:
            return
        
        packet_type = chr(packet_data[0])
        
        try:
            if packet_type == 'S':  # Start packet
                self._handle_start_packet(packet_data, rssi, snr)
            elif packet_type == 'F':  # Fragment packet
                self._handle_fragment_packet(packet_data, rssi, snr)
            elif packet_type == 'E':  # End packet
                self._handle_end_packet(packet_data, rssi, snr)
            else:
                print(f"⚠️  Unknown packet type: {packet_type}")
                
        except Exception as e:
            print(f"❌ Packet handling error: {e}")
    
    def _handle_start_packet(self, packet_data, rssi, snr):
        """Handle start packet"""
        if len(packet_data) < 21:
            print("⚠️  Invalid start packet size")
            return
        
        image_id = packet_data[1:9].decode('utf-8').rstrip('\x00')
        total_size, total_fragments = struct.unpack('<HH', packet_data[9:13])
        start_timestamp = struct.unpack('<d', packet_data[13:21])[0]
        
        self.current_images[image_id] = {
            'id': image_id,
            'total_size': total_size,
            'total_fragments': total_fragments,
            'start_timestamp': start_timestamp,
            'receive_start': time.time(),
            'fragments': {},
            'received_count': 0,
            'rssi_values': [int(rssi)],
            'snr_values': [int(snr)]
        }
        
        print(f"\n📨 🆕 Started receiving image '{image_id}'")
        print(f"   📊 Expected: {total_size} bytes in {total_fragments} fragments")
        print(f"   📡 Signal: RSSI={rssi}dBm, SNR={snr}dB")
        print(f"   🕒 Started at: {datetime.now().strftime('%H:%M:%S')}")
    
    def _handle_fragment_packet(self, packet_data, rssi, snr):
        """Handle fragment packet"""
        if len(packet_data) < 15:
            print("⚠️  Invalid fragment packet size")
            return
        
        image_id = packet_data[1:9].decode('utf-8').rstrip('\x00')
        fragment_id, total_fragments, data_length = struct.unpack('<HHH', packet_data[9:15])
        fragment_data = packet_data[15:15+data_length]
        
        if image_id not in self.current_images:
            print(f"⚠️  Received fragment for unknown image: {image_id}")
            return
        
        # Store fragment (avoid duplicates)
        if fragment_id not in self.current_images[image_id]['fragments']:
            self.current_images[image_id]['fragments'][fragment_id] = fragment_data
            self.current_images[image_id]['received_count'] += 1
        
        self.current_images[image_id]['rssi_values'].append(int(rssi))
        self.current_images[image_id]['snr_values'].append(int(snr))
        
        received = self.current_images[image_id]['received_count']
        total = self.current_images[image_id]['total_fragments']
        
        # Color code RSSI for quick visual feedback
        rssi_val = int(rssi)
        if rssi_val >= -70:
            rssi_status = "🟢"  # Excellent
        elif rssi_val >= -85:
            rssi_status = "🟡"  # Good  
        elif rssi_val >= -100:
            rssi_status = "🟠"  # Fair
        else:
            rssi_status = "🔴"  # Poor
        
        print(f"📨 Fragment {fragment_id+1:2d}/{total} ✅ ({len(fragment_data):3d} bytes) "
              f"Progress: {received:2d}/{total} ({received/total*100:5.1f}%) "
              f"{rssi_status} RSSI={rssi}dBm SNR={snr}dB")
    
    def _handle_end_packet(self, packet_data, rssi, snr):
        """Handle end packet"""
        if len(packet_data) < 17:
            print("⚠️  Invalid end packet size")
            return
        
        image_id = packet_data[1:9].decode('utf-8').rstrip('\x00')
        end_timestamp = struct.unpack('<d', packet_data[9:17])[0]
        
        if image_id not in self.current_images:
            print(f"⚠️  Received end packet for unknown image: {image_id}")
            return
        
        current_image = self.current_images[image_id]
        current_image['end_timestamp'] = end_timestamp
        current_image['receive_end'] = time.time()
        current_image['receive_duration'] = current_image['receive_end'] - current_image['receive_start']
        current_image['transmission_duration'] = end_timestamp - current_image['start_timestamp']
        
        # Calculate signal statistics
        if current_image['rssi_values']:
            current_image['avg_rssi'] = sum(current_image['rssi_values']) / len(current_image['rssi_values'])
            current_image['avg_snr'] = sum(current_image['snr_values']) / len(current_image['snr_values'])
        
        print(f"\n📨 🏁 Completed receiving image '{image_id}'")
        print(f"   📊 Received: {current_image['received_count']}/{current_image['total_fragments']} fragments")
        print(f"   ✅ Success rate: {current_image['received_count']/current_image['total_fragments']*100:.1f}%")
        print(f"   ⏱️  Transmission time: {current_image['transmission_duration']:.2f}s")
        print(f"   ⏱️  Reception time: {current_image['receive_duration']:.2f}s")
        print(f"   📡 Avg signal: RSSI={current_image.get('avg_rssi', 0):.1f}dBm, SNR={current_image.get('avg_snr', 0):.1f}dB")
        
        # RSSI analysis and recommendations
        avg_rssi = current_image.get('avg_rssi', 0)
        rssi_values = current_image.get('rssi_values', [])
        
        if rssi_values:
            rssi_min = min(rssi_values)
            rssi_max = max(rssi_values)
            rssi_range = rssi_max - rssi_min
            
            print(f"   📊 RSSI Analysis: Min={rssi_min}dBm, Max={rssi_max}dBm, Range={rssi_range}dB")
            
            # Signal quality assessment
            if avg_rssi >= -70:
                print(f"   🟢 Signal Quality: EXCELLENT (very strong)")
            elif avg_rssi >= -85:
                print(f"   🟡 Signal Quality: GOOD (reliable)")
            elif avg_rssi >= -100:
                print(f"   🟠 Signal Quality: FAIR (acceptable)")
            else:
                print(f"   🔴 Signal Quality: POOR (consider moving closer)")
            
            # Signal stability assessment
            if rssi_range <= 5:
                print(f"   📈 Signal Stability: VERY STABLE (±{rssi_range/2:.1f}dB)")
            elif rssi_range <= 10:
                print(f"   📈 Signal Stability: STABLE (±{rssi_range/2:.1f}dB)")
            elif rssi_range <= 20:
                print(f"   📈 Signal Stability: MODERATE (±{rssi_range/2:.1f}dB)")
            else:
                print(f"   📈 Signal Stability: UNSTABLE (±{rssi_range/2:.1f}dB) - check environment")
        
        # Try to reconstruct and save image
        if current_image['received_count'] == current_image['total_fragments']:
            reconstructed_image = self._reconstruct_image(current_image)
            if reconstructed_image is not None:
                saved_path = self._save_image(reconstructed_image, image_id)
                current_image['reconstructed'] = True
                current_image['saved_path'] = saved_path
                print(f"   💾 Image saved to: {saved_path}")
                print(f"   🖼️  Image size: {reconstructed_image.shape[1]}x{reconstructed_image.shape[0]} pixels")
            else:
                current_image['reconstructed'] = False
                print(f"   ❌ Failed to reconstruct image")
        else:
            current_image['reconstructed'] = False
            missing = current_image['total_fragments'] - current_image['received_count']
            print(f"   ❌ Incomplete: missing {missing} fragments")
        
        # Store completed image info
        self.completed_images.append(current_image)
        
        # Clean up current image tracking
        del self.current_images[image_id]
        
        print(f"   📈 Total images received: {len(self.completed_images)}")
        print()
    
    def _reconstruct_image(self, image_info):
        """Reconstruct image from fragments"""
        try:
            # Sort fragments by ID and concatenate
            sorted_fragments = sorted(image_info['fragments'].items())
            image_data = b''.join([frag[1] for frag in sorted_fragments])
            
            # Convert bytes to image
            image_array = np.frombuffer(image_data, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            return image
            
        except Exception as e:
            print(f"❌ Image reconstruction failed: {e}")
            return None
    
    def _save_image(self, image, image_id):
        """Save reconstructed image"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{image_id}_{timestamp}.jpg"
        filepath = os.path.join(self.image_save_dir, filename)
        
        cv2.imwrite(filepath, image)
        return filepath
    
    def print_statistics(self):
        """Print reception statistics with detailed RSSI analysis"""
        if not self.completed_images:
            print("📊 No images received yet")
            return
        
        total_images = len(self.completed_images)
        successful_images = sum(1 for img in self.completed_images if img.get('reconstructed', False))
        
        print(f"\n📊 Reception Statistics:")
        print(f"   Total images received: {total_images}")
        print(f"   Successfully reconstructed: {successful_images}")
        print(f"   Success rate: {successful_images/total_images*100:.1f}%")
        
        if self.completed_images:
            avg_duration = sum(img.get('receive_duration', 0) for img in self.completed_images) / total_images
            
            # Collect all RSSI/SNR values
            all_rssi = []
            all_snr = []
            for img in self.completed_images:
                if img.get('rssi_values'):
                    all_rssi.extend(img['rssi_values'])
                if img.get('snr_values'):
                    all_snr.extend(img['snr_values'])
            
            print(f"   Average reception time: {avg_duration:.2f}s")
            
            if all_rssi:
                avg_rssi = sum(all_rssi) / len(all_rssi)
                min_rssi = min(all_rssi)
                max_rssi = max(all_rssi)
                print(f"\n📡 RSSI Analysis (all {len(all_rssi)} fragments):")
                print(f"   Average RSSI: {avg_rssi:.1f}dBm")
                print(f"   RSSI Range: {min_rssi}dBm to {max_rssi}dBm")
                print(f"   RSSI Spread: {max_rssi - min_rssi}dB")
                
                # RSSI quality distribution
                excellent = sum(1 for r in all_rssi if r >= -70)
                good = sum(1 for r in all_rssi if -85 <= r < -70)
                fair = sum(1 for r in all_rssi if -100 <= r < -85)
                poor = sum(1 for r in all_rssi if r < -100)
                
                print(f"   Quality Distribution:")
                print(f"     🟢 Excellent (≥-70dBm): {excellent}/{len(all_rssi)} ({excellent/len(all_rssi)*100:.1f}%)")
                print(f"     🟡 Good (-70 to -85dBm): {good}/{len(all_rssi)} ({good/len(all_rssi)*100:.1f}%)")
                print(f"     🟠 Fair (-85 to -100dBm): {fair}/{len(all_rssi)} ({fair/len(all_rssi)*100:.1f}%)")
                print(f"     🔴 Poor (<-100dBm): {poor}/{len(all_rssi)} ({poor/len(all_rssi)*100:.1f}%)")
            
            if all_snr:
                avg_snr = sum(all_snr) / len(all_snr)
                min_snr = min(all_snr)
                max_snr = max(all_snr)
                print(f"\n📊 SNR Analysis:")
                print(f"   Average SNR: {avg_snr:.1f}dB")
                print(f"   SNR Range: {min_snr}dB to {max_snr}dB")
                
                # SNR quality assessment
                if avg_snr >= 10:
                    print(f"   📶 SNR Quality: EXCELLENT (very clean signal)")
                elif avg_snr >= 5:
                    print(f"   📶 SNR Quality: GOOD (clean signal)")
                elif avg_snr >= 0:
                    print(f"   📶 SNR Quality: FAIR (some noise)")
                else:
                    print(f"   📶 SNR Quality: POOR (noisy signal)")
            
            # Environmental recommendations
            print(f"\n💡 Recommendations:")
            if all_rssi and avg_rssi < -90:
                print(f"   • Consider moving devices closer together")
                print(f"   • Check for obstacles between transmitter and receiver")
                print(f"   • Try repositioning antennas for better line of sight")
            elif all_rssi and max_rssi - min_rssi > 15:
                print(f"   • Signal varies significantly - check for interference")
                print(f"   • Consider stabilizing device positions")
            else:
                print(f"   • Signal quality is good for current setup")
                print(f"   • Current distance and positioning work well")
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.connection:
            self.connection.close()


def main():
    """Main receiver application"""
    print("📡 RAK3172 LoRa Image Receiver")
    print("=" * 50)
    
    # Get COM port
    port = input("Enter Receiver COM port (e.g., COM11): ")
    
    # Initialize receiver
    receiver = RAK3172ImageReceiver(port)
    
    if not receiver.initialize_hardware():
        print("❌ Failed to initialize receiver")
        return
    
    try:
        # Start listening
        receiver.start_listening()
        
    except KeyboardInterrupt:
        print("\n🛑 Receiver stopped by user")
    
    finally:
        # Print final statistics
        receiver.print_statistics()
        receiver.cleanup()
        print("✅ Receiver cleanup completed")


if __name__ == "__main__":
    main()