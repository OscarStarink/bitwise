from rattle import *

@module
class Decoder:
	opt = input(bit[8])
	
	inc = output( opt == ord('+') )
	dec = output( opt == ord('-') )
	
	left = output( opt == ord('<') )
	right = output( opt == ord('>') )
	
	putc = output( opt == ord('.') )
	getc = output( opt == ord(',') )
	
	loop = output( opt == ord('[') )
	lend = output( opt == ord(']') )

@module
class Incrementor:
	N = 8 # Can we do generics?
	i = input(bit[N])
	inc = input(bit)
	dec = input(bit)
	
	# Implement fancy counter here
	val = when( inc | dec, i + when(inc, bit[N](1), bit[N](-1) ) , i )

	o = output(val)


# When enabled, Top uses register() instead of emulated register (_in & _out pairs), which will trigger the 'Cyclic node graph'
false_cycle = True

@module
class Top:
	opt = input(bit[8])
	mem_in = input(bit[8])
	ip_in = input(bit[8])
	sp_in = input(bit[8])
	
	tx_ready = input(bit)
	rx_valid = input(bit)
	rx_in = input(bit[8])
	
	seek_back_in = input(bit)
	seek_forward_in = input(bit)
	interpret_in = ~seek_back_in  & ~seek_forward_in
	
	brace_in = input(bit[8]) 
	
	if false_cycle:
		brace = register(bit[8]) 
	else:
		brace = brace_in
	
	decode = Decoder(opt = opt)
	
	stall = decode.putc & ~tx_ready | decode.getc & ~rx_valid
	
	mem_null = mem_in == 0
	brace_null = brace == 0
	
	seek_forward = mem_null & interpret_in & decode.loop | seek_forward_in & ~(brace_null & decode.lend)
	seek_back = ~mem_null & interpret_in & decode.lend | seek_back_in & ~(brace_null & decode.loop)
	
	interpret = ~seek_back & ~seek_forward
	
	mem = when(decode.getc & rx_valid, rx_in, mem_in)
	
	sp = Incrementor(inc=decode.right & interpret_in, dec=decode.left & interpret_in, i=sp_in)
	ip = Incrementor(inc=~stall & interpret | seek_forward, dec=seek_back, i=ip_in )
	alu = Incrementor(inc=decode.inc & interpret_in, dec=decode.dec & interpret_in, i=mem)
	

	# TODO ALU could be used to update brace counter
	brace_inc = Incrementor( i=brace, inc=seek_forward_in & decode.loop | seek_back_in & decode.lend, dec=(seek_forward_in & decode.lend | seek_back_in & decode.loop ) & ~brace_null )
	
	if false_cycle:
		brace.next = brace_inc.o
	
	seek_back_out = output(seek_back)
	seek_forward_out = output(seek_forward)
	
	
	rx_ready = output(decode.getc & interpret_in)
	tx_valid = output(decode.putc & interpret_in)
	tx_out = output(mem_in)
	
	brace_out = output(brace_inc.o)
	ip_out = output(ip.o)
	sp_out = output(sp.o)
	mem_out = output(alu.o)


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
		self.i = 1
		self.top.ip_out = 0
		self.top.sp_out = 0
		self.top.mem_out = 0
		self.stack = [0]*256
		self.stdout = []
		self.top.tx_ready = True
		
		self.top.brace_out = 0
		self.top.seek_forward_out = False
		self.top.seek_back_out = False
		
		
	def steps(self, n):
		for _ in range(n):
			self.step()
	
	def step(self):
		self.top.ip_in = self.top.ip_out
		self.top.sp_in = self.top.sp_out
		self.top.mem_in = self.stack[self.top.sp_out]
		self.top.opt = self.prog[self.top.ip_out]
		
		self.top.seek_forward_in = self.top.seek_forward_out
		self.top.seek_back_in = self.top.seek_back_out
		self.top.brace_in = self.top.brace_out
		
		self.top.rx_in = self.stdin[0] if len(self.stdin) else 0
		self.top.rx_valid = len(self.stdin) > 0
		
		if False:
			mode = 'interpret'
			if self.top.seek_forward_in:
				mode = 'forward'
			if self.top.seek_back_in:
				mode = 'back'
		
			print("in {} {} {} {}".format(self.i, chr(self.top.opt), self.top.brace_in, mode) )
		
		
		self.top.update(**self.kwargs)
		
		
		self.i = self.i + 1
		
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
	

def test_loop_cond():
	sim = Sim(top, [ ord(x) for x in "+[.-]." ] )
	sim.steps(2)
	assert sim.top.seek_forward_out == False
	sim.steps(3)
	assert sim.top.seek_back_out == False
	sim.step()
	assert sim.stdout == [1, 0]
	
def test_loop_skip():
	sim = Sim(top, [ ord(x) for x in "[.]." ] )
	sim.step()
	assert sim.top.seek_forward_out == True
	sim.steps(3)
	assert sim.stdout == [0]
	assert sim.top.brace_out == 0
	
def test_loop_rewind():
	sim = Sim(top, [ ord(x) for x in "+++[.-]." ] )
	sim.steps(7)
	assert sim.top.seek_back_out == True
	sim.steps(4)
	assert sim.stdout == [3, 2]
	sim.steps(6)
	assert sim.stdout == [3, 2, 1]
	sim.steps(3)
	assert sim.stdout == [3, 2, 1, 0]
	assert sim.top.brace_out == 0

def test_loop_nested():
	sim = Sim(top, [ ord(x) for x in "+++[>+++[>+++<-]<-]>>." ] )
	sim.steps(166)
	assert sim.stdout == [3*3*3]

def test_hello_world():
	sim = Sim(top, [ ord(x) for x in "+[-[<<[+[--->]-[<<<]]]>>>-]>-.---.>..>.<<<<-.<+.>>>>>.>.<<.<-."])
	sim.steps(22704)
	assert sim.stdout == [ord(x) for x in "hello world"]

def test():
	test_add_sub()
	test_move()
	test_print()
	test_read()
	test_loop_cond()
	test_loop_skip()
	test_loop_rewind()
	test_loop_nested()
	test_hello_world()
	
test()

