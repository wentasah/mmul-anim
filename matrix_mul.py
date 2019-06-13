#!/usr/bin/env python3
#
# Copyright 2019 Michal Sojka <michal.sojka@cvut.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import cairo as c
import argparse
from subprocess import Popen, PIPE

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--title', type=str, default="")
parser.add_argument('--L1', metavar='size', type=int, default=0, help='L1 cache size')
parser.add_argument('--block1', metavar='size', type=int, default=12, help='Inner block size')
parser.add_argument('--block2', metavar='size', type=int, default=12, help='Outer block size')
parser.add_argument('--linear', action='store_true', help='Show as linear memory')
parser.add_argument('--output', '-o', default='matrix_mul.pdf', help='Output PDF file (default: %(default)s)')
parser.add_argument('--transpose', action='store_true', help='Transpose matrix B')
parser.add_argument('--pdf', action='store_true', help='Generate PDF')

args = parser.parse_args()

if args.pdf:
    surface = c.PDFSurface(args.output, 380, 200)
    pdf = True
else:
    pdf = False
    png_scale = 3
    surface = c.ImageSurface(c.FORMAT_RGB24, 380*png_scale, 200*png_scale)
ctx = c.Context(surface)

if not pdf:
    ctx.scale(png_scale, png_scale)
    ffmpeg = Popen('ffmpeg -y -f png_pipe -r 24 -i - -vcodec h264 -r 24 -f mp4'.split() + [ args.output ], stdin=PIPE)

class Save:
    def __init__(self, ctx):
        self.ctx = ctx
    def __enter__(self):
        self.ctx.save()
    def __exit__(self, exc_type, exc_value, traceback):
        self.ctx.restore()

class Translate:
    def __init__(self, ctx, dx, dy):
        self.ctx = ctx
        self.dx = dx
        self.dy = dy
    def __enter__(self):
        self.ctx.save()
        self.ctx.translate(self.dx, self.dy)
    def __exit__(self, exc_type, exc_value, traceback):
        self.ctx.restore()

class Scale:
    def __init__(self, ctx, sx, sy):
        self.ctx = ctx
        self.sx = sx
        self.sy = sy
    def __enter__(self):
        self.ctx.save()
        self.ctx.scale(self.sx, self.sy)
    def __exit__(self, exc_type, exc_value, traceback):
        self.ctx.restore()

ctx.set_operator(c.OPERATOR_SOURCE)

class Matrix:
    size = 12
    L1_size = args.L1 # in cache lines
    L2_size = 8      # in cache lines
    cache_line_size = 2 # must be power of 2

    def __init__(self, name, transpose = False):
        self.cache = list()
        self.last_access = (None, None)
        self.name = name
        self.transpose = transpose
        self.accesses = 0
        self.L1_hits = 0
        self.L2_hits = 0

    def xy2cache(self, x, y):
        return (y * self.size + x) & ~(self.cache_line_size - 1)


    def cache2xy(self, tag):
        l = list()
        for i in range(self.cache_line_size):
            addr = tag + i
            x,y = (addr % self.size,
                   addr // self.size)
            l.append((x, y))
        return l

    def access(self, y, x):
        if self.transpose:
            x,y = y,x
        self.accesses += 1
        self.last_access = (x, y)
        tag = self.xy2cache(x, y)
        try:
            i = self.cache.index(tag)
            del self.cache[i]
            if i < self.L1_size:
                self.L1_hits += 1
            else:
                self.L2_hits += 1
        except ValueError:
            pass
        self.cache.insert(0, tag)
        if len(self.cache) > self.L2_size:
            del self.cache[self.L2_size]

class MatrixDrawer:
    def __init__(self, matrix):
        self.matrix = matrix
        self.draw()

    def draw(self):
        with Save(ctx):
            self.set_scale()
            self.show_name()
            with Save(ctx):
                if self.matrix.L1_size > 0:
                    self.show_stat("mem:%-3d L1 hit:%-3d L2 hit:%-3d" %
                                   (self.matrix.accesses, self.matrix.L1_hits, self.matrix.L2_hits))
                else:
                    self.show_stat("mem:%-3d cache hit:%-3d" %
                                   (self.matrix.accesses, self.matrix.L2_hits))
            self.draw_cache()
            self.draw_grid()

    def draw_cache(self):
        for i in range(len(self.matrix.cache)):
            tag = self.matrix.cache[i]
            for (x, y) in [self.matrix.cache2xy(tag)[0]]:
                with Save(ctx):
                    self.cache_path(x, y)
                    if i < self.matrix.L1_size:
                        t = (i*1/self.matrix.L1_size/1.0)
                        ctx.set_source_rgb(t, 1, t)
                    else:
                        t = (i*1/self.matrix.L2_size/1.5)
                        ctx.set_source_rgb(1, t, t)
                    ctx.fill()
        if self.matrix.last_access != (None, None):
            with Save(ctx):
                (x, y) = self.matrix.last_access
#                 self.element_path(x, y)
#                 ctx.clip()
                self.element_path(x, y)
                ctx.set_line_width(4/10)
                ctx.stroke()

class MatrixDrawerRect(MatrixDrawer):
    def show_name(self):
        ctx.set_font_size(Matrix.size/12)
        ctx.move_to(0, -0.3)
        ctx.show_text(self.matrix.name+"  ")

    @staticmethod
    def show_stat(stat):
        ctx.set_font_size(Matrix.size/20)
        ctx.show_text(stat)

    def draw_grid(self):
        s = self.matrix.size
        for i in range(self.matrix.size):
            ctx.move_to(0, i)
            ctx.line_to(s, i)
            ctx.stroke()
            ctx.move_to(i, 0)
            ctx.line_to(i, s)
            ctx.stroke()

        ctx.move_to(0, 0)
        ctx.line_to(s, 0)
        ctx.line_to(s, s)
        ctx.line_to(0, s)
        ctx.close_path()
        ctx.stroke()

    def set_scale(self):
        ctx.scale(1/self.matrix.size, 1/self.matrix.size)
        ctx.set_line_width(1/10)

    @staticmethod
    def element_path(x, y):
        ctx.move_to(x, y)
        ctx.line_to(x+1, y+0)
        ctx.line_to(x+1, y+1)
        ctx.line_to(x+0, y+1)
        ctx.close_path()

    def cache_path(self, x, y):
        ctx.move_to(x, y)
        ctx.line_to(x+self.matrix.cache_line_size, y+0)
        ctx.line_to(x+self.matrix.cache_line_size, y+1)
        ctx.line_to(x+0, y+1)
        ctx.close_path()

class MatrixDrawerLine(MatrixDrawer):
    def show_name(self):
        ctx.set_font_size(1.5)
        ctx.move_to(-1.5, 1)
        ctx.show_text(self.matrix.name+"  ")

    @staticmethod
    def show_stat(stat):
        pass

    def draw_grid(self):
        s = self.matrix.size * self.matrix.size
#         for i in range(s):
#             ctx.move_to(i, 0)
#             ctx.line_to(i, 1)
#             ctx.stroke()

        ctx.move_to(0, 0)
        ctx.line_to(s, 0)
        ctx.line_to(s, 1)
        ctx.line_to(0, 1)
        ctx.close_path()
        ctx.stroke()

    def set_scale(self):
        ctx.scale(2/self.matrix.size/self.matrix.size, 2/self.matrix.size/self.matrix.size)
        ctx.set_line_width(1/10)

    def element_path(self, x, y):
        ctx.move_to(y*self.matrix.size+x, 0)
        ctx.rel_line_to(1, 0)
        ctx.rel_line_to(0, 1)
        ctx.rel_line_to(-1, 0)
        ctx.close_path()

    def cache_path(self, x, y):
        ctx.move_to(y*self.matrix.size+x, 0)
        ctx.rel_line_to(Matrix.cache_line_size, 0)
        ctx.rel_line_to(0, 1)
        ctx.rel_line_to(-Matrix.cache_line_size, 0)
        ctx.close_path()

a = Matrix('A')
b = Matrix('B', args.transpose)
c = Matrix('C')

class Stats:
    def __init__(self, a, b, c):
        ac = a.accesses + b.accesses + c.accesses
        L1 = a.L1_hits + b.L1_hits + c.L1_hits
        L2 = a.L2_hits + b.L2_hits + c.L2_hits
        self.mem = ac
        self.L1h = L1
        self.L2h = L2
        self.L1p = 100*L1//ac
        self.L2p = 100*L2//ac
        self.cache = L1 + L2
        self.cachep = 100*self.cache//ac

    def __str__(self):
        return "mem:%(mem)-4d   L1 hits:%(L1h)-4d≅%(L1p)2d%%   L2 hits:%(L2h)-4d≅%(L2p)2d%%   cache hits:%(cache)-4d≅%(cachep)2d%%" % self.__dict__


def draw_matrices():
    with Save(ctx):
        ctx.set_source_rgb (0, 0, 0)
        dist = 1.2
        ctx.translate(20, 25)
        ctx.set_font_size(10)
        ctx.show_text("Matrix multiplication: " + args.title)
        ctx.translate(0, 20)
        ctx.scale(100, 100)
        ctx.set_font_size(1/12)
        with Save(ctx):
            MatrixDrawerRect(a)
        with Translate(ctx, 1.05, 0.5):
            ctx.show_text("×")
        with Translate(ctx, dist, 0):
            MatrixDrawerRect(b)
        with Translate(ctx, 2.25, 0.5):
            ctx.show_text("=")
        with Translate(ctx, 2*dist, 0):
            MatrixDrawerRect(c)
        with Translate(ctx, 0.0, 1.15):
            stat = Stats(a, b, c)
            if args.L1 > 0:
                ctx.show_text("Totals: mem:%(mem)-4d    L1 hits:%(L1h)-4d≅%(L1p)2d%%    L2 hits:%(L2h)-4d≅%(L2p)2d%%    cache hits:%(cache)-4d≅%(cachep)2d%%" % stat.__dict__)
            else:
                ctx.show_text("Totals: mem:%(mem)-4d    cache hits:%(cache)-4d≅%(cachep)2d%%" % stat.__dict__)

def draw_memory():
    with Save(ctx):
        ctx.set_source_rgb (0, 0, 0)
        dist = 5/Matrix.size/Matrix.size
        ctx.translate(20, 175)
        ctx.scale(170, 170)
        with Translate(ctx, 0, 0):
            MatrixDrawerLine(a)
        with Translate(ctx, 0, dist):
            MatrixDrawerLine(b)
        with Translate(ctx, 0, 2*dist):
            MatrixDrawerLine(c)

cnt = 0
block2_size = args.block2
block1_size = args.block1
for i2 in range(0, Matrix.size, block2_size):
    for j2 in range(0, Matrix.size, block2_size):
        for k2 in range(0, Matrix.size, block2_size):
            for i1 in range(i2, i2+block2_size, block1_size):
                for j1 in range(j2, j2+block2_size, block1_size):
                    for k1 in range(k2, k2+block2_size, block1_size):
                        for i in range(i1, i1+block1_size):
                            for j in range(j1, j1+block1_size):
                                for k in range(k1, k1+block1_size):
                                    c.access(i, j)
                                    a.access(i, k)
                                    b.access(k, j)

                                    #if cnt < 100:
                                    if True:
                                        if not pdf:
                                            ctx.set_source_rgb(1, 1, 1)
                                            ctx.paint()

                                        draw_matrices()
                                        draw_memory()
                                        if pdf:
                                            surface.show_page()
                                        else:
                                            surface.write_to_png(ffmpeg.stdin)
                                    cnt += 1

print(Stats(a, b, c))

if not pdf:
    ffmpeg.stdin.close()
    ffmpeg.wait()
