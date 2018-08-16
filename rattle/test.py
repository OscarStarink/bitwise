from rattle import *
	
@module
class Dummy:
	i = input(bit[8])
	inc = input(bit)
	dec = input(bit)
	o = output(when( inc | dec, i + when(inc, bit[8](1), bit[8](-1) ) , i ))
	
@module
def Test(IntroduceCycle):
	in1 = input(bit[8])
	
	r1 = register(bit[8])
	r2 = register(bit[8])
	
	out1 = output(r1)
	out2 = output(r2)
	
	in_inc = Dummy(inc=r1[0], dec=r2[0], i=in1)
	
	r1.next = in_inc.o
	r2.next = in_inc.o if IntroduceCycle else 0

def test():

	compile(Test(False))
	generate_dot_file(Test(False))
	
	compile(Test(True))
	generate_dot_file(Test(True))

if __name__ == "__main__":
	test()
