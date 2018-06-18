import numpy as np
import numbers

class UnitGenerator(object):
	num_generators = 0
	def __init__(self,duration=None,frame = 0):
		UnitGenerator.num_generators += 1

		self.frame = frame

		self.range = (-1,1)

		self.reused_frame_data = None
		self.reused_continue_flag = None
		self.used_times = 0

		self.num_channels = 1

		self.duration = duration

		self.frame_id = 1

	def __mul__(self,other):
		return Multiply(self,other)

	def __rmul__(self,other):
		return Multiply(self,other)

	def __add__(self,other):
		return Add(self,other)

	def __radd__(self,other):
		return Add(self,other)

	def __truediv__(self,other):
		return Multiply(self,MultiplicativeInverse(other))

	def __rtruediv__(self,other):
		return Multiply(self,MultiplicativeInverse(other))

	def __sub__(self,other):
		return Add(self,AdditiveInverse(other))

	def __rsub__(self,other):
		return Add(self,AdditiveInverse(other))
		
	def __neg__(self):
		return AdditiveInverse(self)

	def set_frame(self, frame):
		self.frame = frame

	def set_generator(self,generator):
		self.generator = generator

	def remove_generator(self):
		self.generator = None

	def generate(self,frame_id,num_frames,sample_rate):
		if not (self.frame_id == frame_id) or frame_id == 2:

			data = self.__generate__(frame_id,num_frames,sample_rate)

			self.frame += num_frames
			
			if self.duration:
				if self.frame/float(sample_rate) > self.duration:
					self.reused_continue_flag = False
				else:
					self.reused_continue_flag = True
			else:
				self.reused_continue_flag = True

			self.reused_frame_data = data

			self.frame_id = frame_id

		return (self.reused_frame_data,self.reused_continue_flag)

	def __generate__(self,frame_id,num_frames,sample_rate):
		# This is the internal version of the generate function. This will be defined by
		# each specific unit generator, and 
		raise ValueError("Did not properly set up __generate__ function on class ", self.__class__)

class Add(UnitGenerator):
	def __init__(self,sig1,sig2):
		super().__init__()
		assert isinstance(sig1,UnitGenerator) or isinstance(sig1,numbers.Real)
		assert isinstance(sig2,UnitGenerator) or isinstance(sig2,numbers.Real)
		self.sig1 = sig1
		self.sig2 = sig2

	def __generate__(self, frame_id,num_frames,sample_rate):
		if isinstance(self.sig1,UnitGenerator):
			[frame_data1, continue_flag1] = self.sig1.generate(frame_id,num_frames,sample_rate)
		else:
			frame_data1 = self.sig1
		if isinstance(self.sig2,UnitGenerator):
			[frame_data2, continue_flag2] = self.sig2.generate(frame_id,num_frames,sample_rate)
		else:
			frame_data2 = self.sig2

		return frame_data1 + frame_data2

class Multiply(UnitGenerator):
	def __init__(self,sig1,sig2):
		super().__init__()
		assert isinstance(sig1,UnitGenerator) or isinstance(sig1,numbers.Real)
		assert isinstance(sig2,UnitGenerator) or isinstance(sig2,numbers.Real)
		self.sig1 = sig1
		self.sig2 = sig2

	def __generate__(self, frame_id,num_frames,sample_rate):
		if isinstance(self.sig1,UnitGenerator):
			[frame_data1, continue_flag1] = self.sig1.generate(frame_id,num_frames,sample_rate)
		else:
			frame_data1 = self.sig1
		if isinstance(self.sig2,UnitGenerator):
			[frame_data2, continue_flag2] = self.sig2.generate(frame_id,num_frames,sample_rate)
		else:
			frame_data2 = self.sig2

		return frame_data1 * frame_data2

class Scale(UnitGenerator):
	def __init__(self,generator,out_range):
		super().__init__()
		in_range = generator.range
		multiplier = (in_range[1]-in_range[0])/(out_range[1]-out_range[0])
		offset = (in_range[1]+in_range[0]+out_range[1]+out_range[0])/2

		self.generator = generator/multiplier+offset

	def __generate__(self,frame_id,num_frames,sample_rate):
		(data,continue_flag) = self.generator.generate(frame_id,num_frames,sample_rate)
		return data

class AdditiveInverse(UnitGenerator):
	def __init__(self,generator):
		super().__init__()
		self.generator = generator

	def __generate__(self,frame_id,num_frames,sample_rate):
		if isinstance(self.generator,UnitGenerator):
			data,continue_flag = self.generator.generate(frame_id,num_frames,sample_rate)
			return -data
		else:
			return -self.generator

class MultiplicativeInverse(UnitGenerator):
	def __init__(self,generator):
		super().__init__()
		self.generator = generator

	def __generate__(self,frame_id,num_frames,sample_rate):
		if isinstance(self.generator,UnitGenerator):
			data,continue_flag = self.generator.generate(frame_id,num_frames,sample_rate)
			return 1/data
		else:
			return 1/self.generator

class ZeroGen(UnitGenerator):
	def __init__(self):
		super().__init__()

	def __generate__(self,frame_id,num_frames,sample_rate):
		return np.zeros(num_frames)