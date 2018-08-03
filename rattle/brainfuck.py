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
	
	tx_ready = input(bit)
	rx_valid = input(bit)
	rx_in = input(bit[8])
	
	
	
	inc = opt == ord('+') 
	sub = opt == ord('-')
	
	left = opt == ord('<')
	right = opt == ord('>')
	
	
	putc = opt == ord('.')
	getc = opt == ord(',')
	
	stall = putc & ~tx_ready | getc & ~rx_valid
	
	sp = when( left | right, sp_in + when(right, bit[8](1), bit[8](-1) ) , sp_in )
	
	
	#ip = add(ip_in, bit[8](1) )
	ip = when( stall, ip_in, ip_in + bit[8](1) )
	
	mem = when(inc | sub, mem_in + when(inc, bit[8](1), bit[8](-1) ) , when(getc & rx_valid, rx_in, mem_in))	
	
	rx_ready = output( getc )
	tx_valid = output( putc )
	tx_out = output( mem_in )
	
	ip_out = output(ip)
	sp_out = output(sp)
	mem_out = output(mem)
	
	
open('example.dot', 'w').write(generate_dot_file(Top))


top = compile(Top, trace_all=True)

class Sim:
	def __init__(self, cls, prog, stdin=[], **kwargs):
		self.top = cls()
		self.prog = prog
		self.stdin = stdin.copy()
		self.reset()
		self.kwargs = kwargs
	
	def reset(self):
		self.top.ip_out = 0
		self.top.sp_out = 0
		self.top.mem_out = 0
		self.stack = [0]*256
		self.stdout = []
		self.top.tx_ready = True
		
	def steps(self, n):
		for _ in range(n):
			self.step()
	
	def step(self):
		self.top.ip_in = self.top.ip_out
		self.top.sp_in = self.top.sp_out
		self.top.mem_in = self.stack[self.top.sp_out]
		self.top.opt = self.prog[self.top.ip_out]
		
		
		self.top.rx_in = self.stdin[0] if len(self.stdin) else 0
		self.top.rx_valid = len(self.stdin) > 0
		
		self.top.update(**self.kwargs)
		
		self.stack[self.top.sp_in] = self.top.mem_out
		if self.top.tx_valid and self.top.tx_ready:
			self.stdout.append(self.top.tx_out)
			
		if self.top.rx_valid and self.top.rx_ready:	
			self.stdin.pop(0)


def test_add_sub():
	sim = Sim(top, [ ord(x) for x in "++-" ], trace=True )
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

def test_print():
	sim = Sim(top, [ ord(x) for x in "++++.+.." ] )
	sim.steps(7)
	assert sim.stdout[0] == 4 
	assert sim.stdout[1] == 5 
	sim.top.tx_ready = False
	sim.steps(10)
	assert len(sim.stdout) == 2
	sim.top.tx_ready = True
	sim.step()
	assert sim.stdout[2] == 5
	
def test_read():
	stdin = [ord(x) for x in "bar"]
	sim = Sim(top, [ ord(x) for x in ",>,>,.<.<." ], stdin )
	sim.steps(10)
	assert sim.stdout == list(reversed(stdin))
	

def test():
	test_add_sub()
	test_move()
	test_print()
	test_read()

test()

