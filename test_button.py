import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library

def button_callback(channel, number):
    print(f"Button {number} was pushed!")

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 16 to be an input pin and set initial value to be pulled low (off)
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 13 to be an input pin and set initial value to be pulled low (off)
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 15 to be an input pin and set initial value to be pulled low (off)
GPIO.setup(31, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 31 to be an input pin and set initial value to be pulled low (off)
# Pass number 1 to the callback using lambda, with 200ms debounce time
GPIO.add_event_detect(16, GPIO.RISING, callback=lambda channel: button_callback(channel, 1), bouncetime=200) # Setup event on pin 16 rising edge
GPIO.add_event_detect(13, GPIO.RISING, callback=lambda channel: button_callback(channel, 2), bouncetime=200) # Setup event on pin 13 rising edge
GPIO.add_event_detect(15, GPIO.RISING, callback=lambda channel: button_callback(channel, 3), bouncetime=200) # Setup event on pin 16 rising edge
GPIO.add_event_detect(31, GPIO.RISING, callback=lambda channel: button_callback(channel, 4), bouncetime=200) # Setup event on pin 31 rising edge

message = input("Press enter to quit\n\n") # Run until someone presses enter

GPIO.cleanup() # Clean up