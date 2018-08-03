from rattle import *

@module
class Add3:
    x = input(bit)
    y = input(bit)
    ci = input(bit)
    p = x ^ y
    g = x & y
    s = output(p ^ ci)
    co = output(g | (p & ci))
    # co = output((x & y) | (x & ci) | (y & ci))

def add3(x, y, c):
    adder = Add3(x=x, y=y, ci=c)
    return adder.s, adder.co

def adc(x, y, c=0):
    s = []
    for xi, yi in zip(x, y):
        si, c = add3(xi, yi, c)
        s.append(si)
    return bits(s), c

def add(x, y, c=0):
    s, c = adc(x, y, c)
    return s

@module
class Top:
	opt = input(bit[8])
	mem_in = input(bit[8])
	ip_in = input(bit[8])
	sp_in = input(bit[8])
	
	
	inc = opt == ord('+') 
	sub = opt == ord('-')
	
	left = opt == ord('<')
	right = opt == ord('>')
	
	
	sp = when( left | right, sp_in + when(right, bit[8](1), bit[8](-1) ) , sp_in )
	
	
	#ip = add(ip_in, bit[8](1) )
	ip = ip_in + bit[8](1)
	
	mem = when(inc | sub, mem_in + when(inc, bit[8](1), bit[8](-1) ) , mem_in)
	
	
	
	ip_out = output(ip)
	sp_out = output(sp)
	mem_out = output(mem)
	
	
open('example.dot', 'w').write(generate_dot_file(Top))


top = compile(Top)

class Sim:
	def __init__(self, cls, prog):
		self.top = cls()
		self.prog = prog
		self.reset()
	
	def reset(self):
		self.top.ip_out = 0
		self.top.sp_out = 0
		self.top.mem_out = 0
		self.stack = [0]*256
		
	def steps(self, n):
		for _ in range(n):
			self.step()
	
	def step(self):
		self.top.ip_in = self.top.ip_out
		self.top.sp_in = self.top.sp_out
		self.top.mem_in = self.stack[self.top.sp_out]
		self.top.opt = self.prog[self.top.ip_out]
		
		self.top.update()
		
		self.stack[self.top.sp_in] = self.top.mem_out
	


def test_add_sub():
	sim = Sim(top, [ ord(x) for x in "++-" ] )
	sim.steps(2)
	assert sim.stack[0] == 2
	sim.step()
	assert sim.stack[0] == 1
	
def test_move():
	sim = Sim(top, [ ord(x) for x in ">>+<+" ] )
	sim.steps(3)
	assert sim.stack[2] == 1
	sim.steps(2)
	assert sim.stack[1] == 1

def test():
	test_add_sub()
	test_move()

test()

