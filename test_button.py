import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library

def button_callback(channel, number):
    print(f"Button {number} was pushed!")

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)

# Pass number 1 to the callback using lambda, with 200ms debounce time
GPIO.add_event_detect(10, GPIO.RISING, callback=lambda channel: button_callback(channel, 1), bouncetime=200) # Setup event on pin 10 rising edge

message = input("Press enter to quit\n\n") # Run until someone presses enter

GPIO.cleanup() # Clean up