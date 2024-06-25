from pynput import mouse

def WriteToFile(x,y):
    with open('keyboard2.txt', 'a') as f:
        print((x,y))
        f.write(f"[{x},{y}]")

with mouse.Listener(on_move=WriteToFile) as l:
    l.join()