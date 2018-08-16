from rattle import *
import unittest

#TODO
# Use register() memory and clean up mem interface
# Use generics for CPU word width and address width
# Improve simulation


@module
class Decoder:
	opt = input(bit[8])
	inc  = output( opt == ord('+') )
	dec  = output( opt == ord('-') )
	left = output( opt == ord('<') )
	right= output( opt == ord('>') )
	putc = output( opt == ord('.') )
	getc = output( opt == ord(',') )
	loop = output( opt == ord('[') )
	lend = output( opt == ord(']') )
	brk  = output( opt == ord('#') )
	halt = output( opt == ord('@') )

@module
class Incrementor:
	N = 8 # Can we do generics?
	i = input(bit[N])
	inc = input(bit)
	dec = input(bit)
	
	# Implement fancy counter here
	val = when( inc | dec, i + when(inc, bit[N](1), bit[N](-1) ) , i )

	o = output(val)


@module
class CPU:
	addr_width = 8

	tx_ready = input(bit)
	tx_valid = output(bit)
	tx_out = output(bit[8])

	rx_ready = output(bit)
	rx_valid = input(bit)
	rx_in = input(bit[8])

	cont = input(bit)
	brk = output(bit)
	halt = output(bit)

	opt_addr = output(bit[addr_width])
	opt = input(bit[8])

	mem_addr = output(bit[addr_width])
	mem_out = output(bit[8])
	mem_in = input(bit[8])
	mem_write = output(bit)

	ip = register(bit[addr_width])
	sp = register(bit[addr_width])
	brace = register(bit[8])

	seek_back = register(bit)
	seek_forward = register(bit)
	interpret = ~seek_back  & ~seek_forward

	decode = Decoder(opt = opt)
	
	stall = output( decode.putc & ~tx_ready | decode.getc & ~rx_valid | decode.halt | decode.brk & ~cont )
	
	mem_null = mem_in == 0
	brace_null = brace == 0
	
	seek_forward.next = mem_null & interpret & decode.loop | seek_forward & ~(brace_null & decode.lend)
	seek_back.next = ~mem_null & interpret & decode.lend | seek_back & ~(brace_null & decode.loop)
	
	interpret_next = ~seek_back.next & ~seek_forward.next
	
	mem = when(decode.getc & rx_valid, rx_in, mem_in)
	
	sp_inc = Incrementor(inc=decode.right & interpret, dec=decode.left & interpret, i=sp)
	ip_inc = Incrementor(inc=~stall & interpret_next | seek_forward.next, dec=seek_back.next, i=ip )
	alu = Incrementor(inc=decode.inc & interpret, dec=decode.dec & interpret, i=mem)
	

	# TODO ALU could be used to update brace counter
	brace_inc = Incrementor( i=brace, inc=seek_forward & decode.loop | seek_back & decode.lend, dec=(seek_forward & decode.lend | seek_back & decode.loop ) & ~brace_null )
	
	brace.next = brace_inc.o
	ip.next = ip_inc.o
	sp.next = sp_inc.o

	brk.out = decode.brk & ~cont & interpret
	halt.out = decode.halt & interpret

	rx_ready.out = decode.getc & interpret
	tx_valid.out = decode.putc & interpret
	tx_out.out = mem_in

	opt_addr.out = ip
	mem_addr.out = sp # sp_inc.o
	mem_out.out = alu.o
	mem_write.out = decode.inc | decode.dec | (decode.getc & rx_valid)

#def mux(addr, data):
#    assert ispow2(len(data))
#    if len(data) == 1:
#        return data[0]
#    else:
#        i = len(data) // 2
#        return when(addr[-1], mux(addr[:-1], data[i:]), mux(addr[:-1], data[:i]))

#@module
#def memory(data_type, size):
#	assert ispow2(size)
#	addr_type = bit[clog2(size)]
#	write_enable = input(bit)
#	write_addr = input(addr_type)
#	write_data = input(data_type)

#	read_addr = input(addr_type)

#	# NOTE Unfortunately rattle doesn't see the array, and creates N anonymous registers.
#	cells = [ register(data_type) for i in range(size) ]
#	# work around
#	for i, cell in enumerate(cells):
#		cell.name = "cells_{}".format(i)

#	# Read-after-write semantics: Bypass write data to read data if addresses match.
#	read_data = output(delay(when(write_enable & (read_addr == write_addr), write_data, mux(read_addr, cells))))

#	for i, cell in enumerate(cells):
#		cell.next = when(write_enable & (write_addr == i), write_data, cell)

#@module
#class Top:
#	tx_ready = input(bit)
#	tx_valid = output(bit)
#	tx_out = output(bit[8])

#	rx_ready = output(bit)
#	rx_valid = input(bit)
#	rx_in = input(bit[8])

#	opt_addr = output(bit[8])
#	opt = input(bit[8])

#	stack = memory(bit[8], 4)()
#	cpu = CPU(mem_in=stack.read_data, tx_ready=tx_ready, rx_valid=rx_valid, rx_in=rx_in, opt=opt)

#	stack.write_data = cpu.mem_out
#	stack.write_enable = cpu.mem_write
#	stack.write_addr = cpu.mem_addr[:2]
#	stack.read_addr = cpu.mem_addr[:2]

#	tx_valid.out = cpu.tx_valid
#	tx_out.out   = cpu.tx_out
#	rx_ready.out = cpu.rx_ready
#	opt_addr.out = cpu.opt_addr

class Sim:
	def __init__(self, cls, prog, stdin=[], **kwargs):
		self.top = cls()
		self.prog = prog + [ord('@')]
		self.stdin = stdin.copy()
		self.reset()
		self.kwargs = kwargs
	
	def reset(self):
		self.i = 1
		self.stack_buf = [0]*256
		self.stdout = []
		self.top.tx_ready = True
		
	def steps(self, n):
		for _ in range(n):
			self.step()

	def run(self):
		self.top.cont = 1 #set cont so next time we continue
		while True:
			self.step()
			if self.top.brk:
				break
			if self.top.halt:
				break

	def stack(self, n):
		#reg = "stack_cells_{}".format(n)
		#if hasattr(self.top, reg):
		#	return getattr(self.top, reg)
		#else:
		#	raise IndexError
		return self.stack_buf[n]

	def step(self):
		self.top.mem_in = self.stack_buf[self.top.sp]
		self.top.opt = self.prog[self.top.ip]
		
		self.top.rx_in = self.stdin[0] if len(self.stdin) else 0
		self.top.rx_valid = len(self.stdin) > 0
		
		dbg = False
		if dbg:
			mode = 'interpret'
			if self.top.seek_forward:
				mode = 'forward'
			if self.top.seek_back:
				mode = 'back'
			print("in {} opt:{} sp:{} ip:{} {} {} cont:{}".format(self.i, chr(self.top.opt), self.top.sp, self.top.ip, self.top.brace, mode, self.top.cont) )
		
		self.top.update(**self.kwargs)

		self.i = self.i + 1
		
		if self.top.mem_write:
			self.stack_buf[self.top.sp] = self.top.mem_out
		if self.top.tx_valid and self.top.tx_ready:
			self.stdout.append(self.top.tx_out)
			
		if self.top.rx_valid and self.top.rx_ready:	
			self.stdin.pop(0)

		self.top.tick()

		# clear continue, so that we dont fall trough the next break
		self.top.cont = 0

		if dbg:
			print("stall:{} ip':{} break:{} halt:{}".format( self.top.stall, self.top.ip, self.top.brk, self.top.halt))


class TestCPUBase():
	def test_halt(self):
		sim = Sim(self.cpu, list(b""))
		sim.run()

	def test_nop(self):
		sim = Sim(self.cpu, list(b"   "))
		sim.run()

	def test_add(self):
		sim = Sim(self.cpu, list(b"++" ))
		sim.run()
		assert sim.stack(0) == 2

	def test_sub(self):
		sim = Sim(self.cpu, list(b"++-"))
		sim.run()
		assert sim.stack(0) == 1

	def test_break(self):
		sim = Sim(self.cpu, list(b"+#+#+"))
		sim.run()
		assert sim.stack(0) == 1
		sim.run()
		assert sim.stack(0) == 2
		sim.run()
		assert sim.stack(0) == 3

	def test_move(self):
		sim = Sim(self.cpu, list(b">>+#<+"))
		sim.run()
		assert sim.stack(2) == 1
		sim.run()
		assert sim.stack(1) == 1

	def test_print(self):
		sim = Sim(self.cpu, list(b"++++.+.#."))
		sim.run()
		assert sim.stdout[0] == 4
		assert sim.stdout[1] == 5
		sim.top.tx_ready = False
		sim.steps(10)
		assert len(sim.stdout) == 2
		sim.top.tx_ready = True
		sim.run()
		assert sim.stdout[2] == 5

	def test_read(self):
		stdin = list(b"bar")
		sim = Sim(self.cpu, list(b",>,>,.<.<."), stdin )
		sim.run()
		assert sim.stdout == list(reversed(stdin))

	def test_loop_cond(self):
		sim = Sim(self.cpu, list(b"+[.-]."))
		sim.run()
		assert sim.stdout == [1, 0]

	def test_loop_skip(self):
		sim = Sim(self.cpu, list(b"[.]."))
		sim.run()
		assert sim.stdout == [0]
		assert sim.top.brace == 0

	def test_loop_rewind(self):
		sim = Sim(self.cpu, list(b"+++[.-]."))
		sim.run()
		assert sim.stdout == [3, 2, 1, 0]
		assert sim.top.brace == 0

	def test_loop_nested(self):
		sim = Sim(self.cpu, list(b"+++[>+++[>+++<-]<-]>>."))
		sim.run()
		assert sim.stdout == [3*3*3]

	def test_hello_world(self):
		sim = Sim(self.cpu, list(b"+[-[<<[+[--->]-[<<<]]]>>>-]>-.---.>..>.<<<<-.<+.>>>>>.>.<<.<-."))
		sim.run()
		assert sim.stdout == list(b"hello world")

	def test_59008(self):
		sim = Sim(self.cpu, list(b"++++[>++++[>++++>+++++++<<-]<-]>>++.>-  (.)(.)  [>+>+<<-]+++[>----<-]>-.>++++."))
		sim.run()
		assert sim.stdout == [66, 111, 111, 98, 115]

class TestCPUV1(unittest.TestCase, TestCPUBase):
	def setUp(self):
		self.cpu = compile(CPU)

if __name__ == '__main__':
    unittest.main()
    #open('Top.dot', 'w').write(generate_dot_file(Top))
    open('CPU.dot', 'w').write(generate_dot_file(CPU))

