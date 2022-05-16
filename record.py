# squinky

from pynput import keyboard
from pynput.mouse import Controller
import mss
import cv2
import time
import numpy as np
from PIL import Image
import threading
import ffmpy
import os
#from pygifsicle import optimize

class App():

    def __init__(self):
        self.mouse_controller = Controller()
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.m1 = None
        self.m2 = None
        self.hotkey = {keyboard.Key.scroll_lock}
        self.isPressed = set()
        self.markingMode = False
        self.recordingMode = False
        self.displayFPS = False
        self.logLine = 0
        self.fps = 30.0
        self.ff = None
        self.filename = None

    def help_menu(self):
        self.menu(" >  INSTRUCTIONS: Select an area you want to record by entering marking mode.")
        self.menu(" >                Use right control to mark the top left and then the bottom right")
        self.menu(" >                corners of the area you want to record. When you are ready, use")
        self.menu(" >                pause button to start recording.")
        self.menu(" >  SCROLL LOCK - activate/deactivate marking mode")
        self.menu(" >  RIGHT CTRL - mark/reset coordinates in marking mode")
        self.menu(" >  PAUSE/BREAK - start/end recording")
        self.menu(" >  ESC - exit")

    def _on_release(self, key):
        try:
            self.isPressed.remove(key)
        except:
            pass
        if key == keyboard.Key.esc and self.recordingMode is False:
            self.menu(" ~ See you for now.")
            return False
        if key == keyboard.Key.pause:
            if self.m1 is not None and self.m2 is not None and self.recordingMode is False:
                if self.markingMode is True:
                    self.markingMode = False
                self.menu(" ~ Starting recording!")
                t = threading.Thread(target=self.record)
                t.start()
            elif self.recordingMode is True:
                self.recordingMode = False
            else:
                self.menu(" X ERROR: missing coordinates")
        if key == keyboard.Key.ctrl_r and self.markingMode is False and self.recordingMode is False:
            self.menu(" X ERROR: not in marking mode")

    def _on_press(self, key):
        try:
            if self.markingMode:
                if self.m1 is None and key == keyboard.Key.ctrl_r:
                    self.menu(" ~ Mark 1 (top left corner)")
                    self.m1 = self.mouse_controller.position
                    self.menu("     x =", self.m1[0], ",", "y =", self.m1[1])
                elif self.m2 is None and key == keyboard.Key.ctrl_r:
                    self.menu(" ~ Mark 2 (bottom right corner)")
                    self.m2 = self.mouse_controller.position
                    self.menu("     x =", self.m2[0], ",", "y =", self.m2[1])
                    if self.m2[0] - self.m1[0] <= 0 or self.m2[1] - self.m1[1] <= 0:
                        self.menu(" X Error: zero or negative position detected. Try again.")
                        self.reset()
                elif self.m1 is not None and self.m2 is not None and key == keyboard.Key.ctrl_r:
                    self.reset()
            if key in self.hotkey:
                self.isPressed.add(key)
            if all(k in self.isPressed for k in self.hotkey) and self.markingMode is True and self.recordingMode is False:
                self.menu(" ~ Exiting marking mode")
                self.markingMode = False
                return
            elif all(k in self.isPressed for k in self.hotkey) and self.recordingMode is False:
                pass
            if all(k in self.isPressed for k in self.hotkey):
                if self.markingMode is False and self.recordingMode is False:
                    self.markingMode = True
                    self.menu(" ~ Activated marking mode: Press RIGHT CTRL to record")
                elif self.recordingMode is False:
                    pass
        except AttributeError:
            self.menu('special key {0} self.isPressed'.format(key))

    def reset(self):
        self.m1 = None
        self.m2 = None
        self.menu(" ~ Reset coordinates")

    def run(self):

        self.keyboard_listener.start()
        self.keyboard_listener.join()

    def menu(self, *s):
        self.logLine += 1
        line = str(self.logLine) + " "
        for s in s:
            line += str(s) + " "
        print(line)
    
    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONUP:
            self.recordingMode = False

    def record(self):
        width = self.m2[0]-self.m1[0]
        height = abs(self.m2[1]-self.m1[1])
        resolution = (width, height) 
        codec = cv2.VideoWriter_fourcc(*"XVID") 
        monitor = {"top": self.m1[1], "left": self.m1[0], "width": width, "height": height}
        current_time = time.strftime("%H_%M_%S", time.localtime())
        self.filename = "{0}-{top}x{left}_{width}x{height}.avi".format(current_time, **monitor)
    
        out = cv2.VideoWriter(self.filename, codec, self.fps, resolution)
        cv2.namedWindow("Preview", cv2.WINDOW_NORMAL) 
        cv2.resizeWindow("Preview", 480, 270)
        cv2.setMouseCallback('Preview', self._on_mouse)
        with mss.mss() as sct:
            self.recordingMode = True
            while self.recordingMode:
                last_time = time.time()
                screenshot = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                cv2.imshow('Preview', frame)
                out.write(frame)
                if (self.displayFPS):
                    try:
                        self.menu("FPS: {}".format(1 / (time.time() - last_time)))
                    except ZeroDivisionError:
                        pass


                if cv2.waitKey(1) & 0xFF == ord("q") or self.recordingMode is False:
                    self.menu(" > Stopping recording!")
                    self.recordingMode = False
                    cv2.destroyAllWindows()
                    break

        t1 = threading.Thread(target=self.convertGIF, args=("{0}".format(self.filename),))
        t1.start()

    def convertGIF(self, filename):

        with open('log.txt', 'a') as f:
            f.write('Start log of {0}\n'.format(filename))
            f.flush()
            basename = filename.split(".")[0]
            ff = ffmpy.FFmpeg(
                inputs={filename: ['-ss', "0.0", '-y']},
                outputs={'{0}.mp4'.format(basename): []}
            )
            ff.run(stdout=f, stderr=f)
            f.write('Done converting to mp4\n')
            f.flush()
            # ff = ffmpy.FFmpeg(
            #     inputs={'{0}.mp4'.format(basename): ['-ss', "0.0", '-y']},
            #     outputs={'{0}.gif'.format(basename): ['-filter_complex', "[0:v] fps=12,scale=w=480:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1"]}
            # )
            # ff.run(stdout=f, stderr=f)
            # f.write('Done converting to gif\n')
            # optimize('{0}.gif'.format(basename))
            # self.menu(" ~ Optimizing gif.. please wait")
            # f.write('Done optimizing gif\n')
            f.write('End log of {0}\n'.format(filename))
        
        self.cleanup()

    def cleanup(self):
        try:
            basename = self.filename.split(".")[0]
            self.menu(' ~ Cleaning up')
            os.remove('{0}.avi'.format(basename))
        except Exception:
            self.menu(" X  File does not exist!")
        self.menu(' ~ Done')




if __name__ == "__main__":
    mainApp = App()
    mainApp.help_menu()
    mainApp.run()

