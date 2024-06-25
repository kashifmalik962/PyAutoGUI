# from pynput.mouse import Controller

# #Mouse Controller
# def MouseController():
#     mouse = Controller()
#     mouse.position = (1000,1000)

# # MouseController()


# #KeyBoard Controller 
# def KeyboardController():
#     keyboard = Controller()
#     keyboard.type('I am a kashif')

# # KeyboardController()



# from pynput import keyboard


# def WriteToFile(key):
#     try:
#         with open('keyboard.txt', 'a') as f:
#             key = str(key)
#             key = key.replace("'","")
#             print(key)
#             if key == 'Key.space':
#                 key = ' '
#             elif key == 'Key.enter':
#                 key  = '\n'
#             f.write(key)
#     except AttributeError:
#         with open('keyboard.txt', 'a') as f:
#             f.write(f'{key}')

# def on_release(key):
#     if key == keyboard.Key.esc:  # Stop listener with Esc key
#         return False
    

# with keyboard.Listener(on_press=WriteToFile, on_release=on_release) as l:
#     l.join()



from pynput import mouse

def on_click(x, y, button, pressed):
    if pressed:
        with open('keyboard.txt','a') as f:
            f.write(f"[{x},{y},{str(button)}],\n")


# Set up the listener
with mouse.Listener(on_click=on_click) as listener:
    listener.join()
