import glfw
import glfw.GLFW as GLFW_CONSTANTS
from OpenGL.GL import *
import numpy as np
import ctypes
from OpenGL.GL.shaders import compileProgram,compileShader
import pyrr
from PIL import Image

SCREEN_WIDTH=640 #640
SCREEN_HEIGHT=480 #480
RETURN_ACTION_CONTINUE=0
RETURN_ACTION_CONTINUE=1

def initialize_glfw():
    glfw.init()
    glfw.window_hint(GLFW_CONSTANTS.GLFW_CONTEXT_VERSION_MAJOR,3)
    glfw.window_hint(GLFW_CONSTANTS.GLFW_CONTEXT_VERSION_MINOR,3)
    glfw.window_hint(GLFW_CONSTANTS.GLFW_OPENGL_PROFILE,GLFW_CONSTANTS.GLFW_OPENGL_CORE_PROFILE)

    glfw.window_hint(GLFW_CONSTANTS.GLFW_OPENGL_FORWARD_COMPAT,GLFW_CONSTANTS.GLFW_TRUE)
    glfw.window_hint(GLFW_CONSTANTS.GLFW_DOUBLEBUFFER,GL_FALSE)
    glfw.window_hint(glfw.RESIZABLE,True)

    window = glfw.create_window(SCREEN_WIDTH,SCREEN_HEIGHT,"Noam/'s voxel engine",None,None)
    glfw.make_context_current(window)
    glfw.set_input_mode(window,GLFW_CONSTANTS.GLFW_CURSOR,GLFW_CONSTANTS.GLFW_CURSOR_HIDDEN)

    return window

class Cube:
    def __init__(self,position,eulers):
        self.position = np.array(position,dtype=np.float32)
        self.eulers = np.array(eulers,dtype=np.float32)

class Player:

    def __init__(self,position):
        self.position = np.array(position,dtype=np.float32)
        self.theta=0
        self.phi=0
        self.update_vectors()


    def update_vectors(self):
        self.forwards = np.array(
            [
                np.cos(np.deg2rad(self.theta)) * np.cos(np.deg2rad(self.phi)),
                np.sin(np.deg2rad(self.theta)) * np.cos(np.deg2rad(self.phi)),
                np.sin(np.deg2rad(self.phi)),
            ]
        )
        globalUp = np.array([0, 0, 1], dtype=np.float32)
        self.right = np.cross(self.forwards, globalUp)
        self.up = np.cross(self.right, self.forwards)
class Scene:
    def __init__(self):

        self.cubes=[

        ]
        for x in range(3):
            for y in range(3):
                for z in range(3):
                    self.cubes.append(Cube([x,y,z],[0,0,0]))

        self.player=Player(position=[0,0,2])
    def update(self,rate):
        for cube in self.cubes:
            cube.eulers[1]+=0.25*rate
            if cube.eulers[1]>360:
                cube.eulers[1]-=360
    def move_player(self,dPos):
        dPos=np.array(dPos,dtype=np.float32)
        self.player.position+=dPos
    def spin_player(self,dTheta,dPhi):
        self.player.theta+=dTheta
        if self.player.theta>360:
            self.player.theta-=360
        elif self.player.theta<0:
            self.player.theta+=360

        self.player.phi=min(89,max(-89,self.player.phi+dPhi))
        self.player.update_vectors()

class GraphicsEngine:
    def __init__(self):
        self.cube_mesh = CubeMesh()
        self.texture = Material("gfx/gr.jpg")  # oak_planks.png wood.jpeg cat.png")


        # initialize gl
        glClearColor(0.0, 0.7, 1, 1)
        self.shader = self.createShader("shaders/vertex.txt", "shaders/fragment.txt")
        glUseProgram(self.shader)
        glUniform1i(glGetUniformLocation(self.shader, "imageTexture"), 0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)

        glFrontFace(GL_CW)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        projection_transform = pyrr.matrix44.create_perspective_projection(
            fovy=45, aspect=SCREEN_WIDTH / SCREEN_HEIGHT,
            near=0.1, far=100, dtype=np.float32
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader, "projection"),
            1, GL_FALSE, projection_transform
        )

        self.modelMatrixLocation = glGetUniformLocation(self.shader, "model")
        self.viewMatrixLocation= glGetUniformLocation(self.shader, "view")

    def createShader(self, vertexFilepath, fragmentFilepath):
        with open(vertexFilepath, 'r') as f:
            vertex_src = f.readlines()
        with open(fragmentFilepath, 'r') as f:
            fragment_src = f.readlines()

        shader = compileProgram(
            compileShader(vertex_src, GL_VERTEX_SHADER),
            compileShader(fragment_src, GL_FRAGMENT_SHADER)
        )
        return shader
    def render(self,scene):
        # refresh screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.shader)

        view_transform = pyrr.matrix44.create_look_at(
            eye=scene.player.position,
            target=scene.player.position+scene.player.forwards,
            up=scene.player.up,
            dtype=np.float32)

        glUniformMatrix4fv(self.viewMatrixLocation, 1, GL_FALSE, view_transform)
        self.texture.use()
        glBindVertexArray(self.cube_mesh.vao)



        # 1. Create transform matrices from scene
        instance_transforms = []
        for cube in scene.cubes:
            m = pyrr.matrix44.create_from_translation(cube.position, dtype=np.float32)
            instance_transforms.append(m)
        instance_transforms = np.array(instance_transforms, dtype=np.float32)

        # 2. Upload to GPU
        glBindBuffer(GL_ARRAY_BUFFER, self.cube_mesh.instance_vbo)
        glBufferData(GL_ARRAY_BUFFER, instance_transforms.nbytes, instance_transforms, GL_STREAM_DRAW)

        # 3. Draw
        glDrawArraysInstanced(GL_TRIANGLES, 0, self.cube_mesh.vertex_count, len(scene.cubes))

        glfw.swap_buffers(window)


    def quit(self):
        self.cube_mesh.destroy()
        self.texture.destroy()
        glDeleteProgram(self.shader)

class App:

    def __init__(self,window):

        #initialize pg
        self.window=window
        self.renderer = GraphicsEngine()
        self.scene = Scene()

        self.lastTime=glfw.get_time()
        self.currentTime=0
        self.numFrames=0
        self.frameTime=0

        self.walk_offset_lookup={
            1:0,
            2:90,
            3: 45,
            4: 180,
            6: 135,
            7: 90,
            8: 270,
            9: 315,
            11: 0,
            12: 225,
            13: 270,
            14: 180
        }



        self.mainLoop()

    def mainLoop(self):
            running = True
            while running:
                #check events
               if glfw.window_should_close(self.window) \
                   or glfw.get_key(self.window,GLFW_CONSTANTS.GLFW_KEY_ESCAPE)==GLFW_CONSTANTS.GLFW_PRESS:
                   running=False

               self.handleKeys()

               self.handleMouse()

               glfw.poll_events()

               self.scene.update(self.frameTime/16.7)
               self.renderer.render(self.scene)
                 #timing (fps)
               self.calculateFramerate()
            self.quit()


    def handleKeys(self):
        """
        w: 1  -> 0  degrees
        a: 2  -> 90 degrees
        w & a: 3 -> 45 degrees
        s: 4  -> 180 degrees
        w & s: 5 -> x
        a & s: 6 -> 135 degrees
        w,a,s: 7 -> 90 degrees
        d: 8->270 degrees
        w & d: 9 -> 315 degrees
        a & d: 10 -> x
        w & a & d: 11 -> 0 degrees
        s & d: 12 ->225 degrees
        w & s & d: 13 -> 270 degrees
        a & s & d: 14 -> 180 degrees
        w & a & s & d: 15 -> x
        """
        combo=0
        directionModifier=0

        if glfw.get_key(self.window,GLFW_CONSTANTS.GLFW_KEY_W)==GLFW_CONSTANTS.GLFW_PRESS:
            combo+=1
        if glfw.get_key(self.window,GLFW_CONSTANTS.GLFW_KEY_A)==GLFW_CONSTANTS.GLFW_PRESS:
            combo+=2
        if glfw.get_key(self.window,GLFW_CONSTANTS.GLFW_KEY_S)==GLFW_CONSTANTS.GLFW_PRESS:
            combo+=4
        if glfw.get_key(self.window,GLFW_CONSTANTS.GLFW_KEY_D)==GLFW_CONSTANTS.GLFW_PRESS:
            combo+=8

        if combo in self.walk_offset_lookup:
            directionModifier=self.walk_offset_lookup[combo]
            dPos=[
                0.1*self.frameTime/ 16.7* np.cos(np.deg2rad(self.scene.player.theta+directionModifier)),
                0.1*self.frameTime / 16.7 * np.sin(np.deg2rad(self.scene.player.theta + directionModifier)),
                0
            ]
        else:
            dPos = [0, 0, 0]  # No horizontal movement

        # Handle vertical movement (space and shift)
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_SPACE) == GLFW_CONSTANTS.GLFW_PRESS:
            dPos[2] += 0.1 * self.frameTime / 16.7

        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_LEFT_CONTROL) == GLFW_CONSTANTS.GLFW_PRESS:
            dPos[2] -= 0.1 * self.frameTime / 16.7

        if dPos != [0, 0, 0]:
             self.scene.move_player(dPos)

    def handleMouse(self):
        (x,y)=glfw.get_cursor_pos(self.window)
        rate=0.05 #self.frameTime / 16.7
        theta_increment=rate * ((SCREEN_WIDTH/2)-x)
        phi_increment = rate * ((SCREEN_HEIGHT / 2) - y)
        self.scene.spin_player(theta_increment, phi_increment)
        glfw.set_cursor_pos(self.window, SCREEN_WIDTH/2, SCREEN_HEIGHT/2)
    def calculateFramerate(self):
        self.currentTime=glfw.get_time()
        delta=self.currentTime - self.lastTime
        if (delta >=1 ):
            framerate=max(1,int(self.numFrames/delta))
            glfw.set_window_title(self.window, f"running at {framerate}")
            self.lastTime=self.currentTime
            self.numFrames=-1
            self.frameTime=float(1000.0/max(1,framerate))
        self.numFrames+=1
    def quit(self):
        self.renderer.quit()

class CubeMesh:
    def __init__(self):
            #x     y     z   s   t

        self.vertices = (
                # Front face (positive Y)
                -0.5, 0.5, -0.5, 0, 1,
                0.5, 0.5, -0.5, 1, 1,
                0.5, 0.5, 0.5, 1, 0,

                0.5, 0.5, 0.5, 1, 0,
                -0.5, 0.5, 0.5, 0, 0,
                -0.5, 0.5, -0.5, 0, 1,

                # Back face (negative Y)
                0.5, -0.5, -0.5, 0, 1,
                -0.5, -0.5, -0.5, 1, 1,
                -0.5, -0.5, 0.5, 1, 0,

                -0.5, -0.5, 0.5, 1, 0,
                0.5, -0.5, 0.5, 0, 0,
                0.5, -0.5, -0.5, 0, 1,

                # Left face (negative X)
                -0.5, -0.5, -0.5, 0, 1,
                -0.5, 0.5, -0.5, 1, 1,
                -0.5, 0.5, 0.5, 1, 0,

                -0.5, 0.5, 0.5, 1, 0,
                -0.5, -0.5, 0.5, 0, 0,
                -0.5, -0.5, -0.5, 0, 1,

                # Right face (positive X)
                0.5, 0.5, -0.5, 0, 1,
                0.5, -0.5, -0.5, 1, 1,
                0.5, -0.5, 0.5, 1, 0,

                0.5, -0.5, 0.5, 1, 0,
                0.5, 0.5, 0.5, 0, 0,
                0.5, 0.5, -0.5, 0, 1,

                # Bottom face (negative Z)
                -0.5, -0.5, -0.5, 0, 1,
                0.5, -0.5, -0.5, 1, 1,
                0.5, 0.5, -0.5, 1, 0,

                0.5, 0.5, -0.5, 1, 0,
                -0.5, 0.5, -0.5, 0, 0,
                -0.5, -0.5, -0.5, 0, 1,

                # Top face (positive Z)
                -0.5, 0.5, 0.5, 0, 1,
                0.5, 0.5, 0.5, 1, 1,
                0.5, -0.5, 0.5, 1, 0,

                0.5, -0.5, 0.5, 1, 0,
                -0.5, -0.5, 0.5, 0, 0,
                -0.5, 0.5, 0.5, 0, 1,
            )
        self.vertex_count = len(self.vertices)//5
        self.vertices = np.array(self.vertices, dtype=np.float32)



        self.vao=glGenVertexArrays(1)
        glBindVertexArray(self.vao)


        self.vbo=glGenBuffers(1) # vbo = vertex buffer object
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20,ctypes.c_void_p(0))

        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))

        #---------------------------------------------------------------------------------
            # === Instance matrix buffer (location = 2–5) ===
        self.instance_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.instance_vbo)

            # Allocate empty space (we fill it per frame)
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_DYNAMIC_DRAW)#GL_STREAM_DRAW GL_DYNAMIC_DRAW

        stride = 64  # 4 vec4s × 4 bytes × 4 floats

        for i in range(4):
                glEnableVertexAttribArray(2 + i)
                glVertexAttribPointer(2 + i, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(i * 16))
                glVertexAttribDivisor(2 + i, 1)  # Advance per instance

    def destroy(self):
        glDeleteVertexArrays(1,(self.vao,))
        glDeleteBuffers(1,(self.vbo,))
        glDeleteBuffers(1, (self.instance_vbo,))

class Material:
    def __init__(self,filepath):
        self.texture=glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D,self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,GL_NEAREST_MIPMAP_LINEAR)#GL_NEAREST
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)#GL_LINEAR

        with Image.open(filepath) as image:
         image_width,image_height=image.size
         image=image.convert('RGBA')
         image_data=bytes(image.tobytes())
         glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,image_data)
        glGenerateMipmap(GL_TEXTURE_2D)

    def use(self):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D,self.texture)

    def destroy(self):
        glDeleteTextures(1,(self.texture,))


window=initialize_glfw()
myApp = App(window)

