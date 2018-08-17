from rattle import *
import unittest


@module
class Dummy:
	i = input(bit[8])
	inc = input(bit)
	dec = input(bit)
	o = output(when( inc | dec, i + when(inc, bit[8](1), bit[8](-1) ) , i ))
	
@module
def Test1(IntroduceCycle):
	in1 = input(bit[8])
	
	r1 = register(bit[8])
	r2 = register(bit[8])
	
	out1 = output(r1)
	out2 = output(r2)
	
	in_inc = Dummy(inc=r1[0], dec=r2[0], i=in1)
	
	r1.next = in_inc.o
	r2.next = in_inc.o if IntroduceCycle else 0

@module
class DoubleInv:
	i1 = input(bit)
	i2 = input(bit)
	o1 = output(~i1)
	o2 = output(~i2)

@module
class Test2:
	i = input(bit)
	inv = DoubleInv(i1=i)
	inv.i2 = inv.o1
	o = output(inv.o2)	
	
class TestCycleNodeGraph(unittest.TestCase):	

	def test_1_false_dot(self):
		generate_dot_file(Test1(False))
		
	def test_1_false_copy(self):
		copy_module(Test1(False))
		
	def test_1_false_compile(self):	
		compile(Test1(False))
		
	def test_1_true_dot(self):
		generate_dot_file(Test1(True))
		
	def test_1_true_copy(self):
		copy_module(Test1(True))
		
	def test_1_true_compile(self):	
		compile(Test1(True))
		
	def test_2_dot(self):
		generate_dot_file(Test2)
		
	def test_2_copy(self):
		copy_module(Test2)
		
	def test_2_compile(self):	
		compile(Test2)
		
if __name__ == "__main__":
	unittest.main()
