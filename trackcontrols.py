import numpy as np
from .unitgenerator import UnitGenerator

class MonoToStereo(UnitGenerator):
	def __init__(self,generator):
		super().__init__()
		self.set_generator(generator)
		self.num_channels = 2

	def generate(self,frame_id,num_frames,sample_rate):
		(data,continue_flag) = self.generator.generate(frame_id,num_frames,sample_rate)
		return np.stack((data,data),axis=1).flatten(), continue_flag

class Mixer(UnitGenerator):
	def __init__(self,generators = [],gain=1):
		super().__init__()
		self.num_channels = 2
		self.generators = generators

	def add(self, gen) :
		if gen.num_channels == 1:
			gen = MonoToStereo(gen)
		self.generators.append(gen)

	def get_num_generators(self) :
		return len(self.generators)

	def __generate__(self,frame_id,num_frames,sample_rate):
		output = np.zeros(num_frames * self.num_channels)

		# this calls generate() for each generator. generator must return:
		# (signal, keep_going). If keep_going is True, it means the generator
		# has more to generate. False means generator is done and will be
		# removed from the list. signal must be a numpay array of length
		# num_frames * num_channels (or less)
		to_remove = []
		for generator in self.generators:
			(data, continue_flag) = generator.generate(frame_id, num_frames, sample_rate)
			output += data
			if not continue_flag:
				to_remove.append(generator)

		# remove generators that are done
		for generator in to_remove:
			self.generators.remove(generator)

		return output

class Panner(UnitGenerator):
	def __init__(self,generator,pan,pan_func="Linear"):
		super().__init__()

		self.num_channels = 2
		self.set_pan_function(pan_func)
		self.set_pan(pan)
		self.set_generator(generator)		

	def set_pan_function(self,func):

		if func == 'Linear':
			self.pan_func = self.__linear_pan__

	def set_pan(self,pan):
		self.pan = pan

	def reset_pan(self):
		self.pan = .5

	def __linear_pan__(self,frame_id,num_frames,sample_rate):
		if isinstance(self.pan,UnitGenerator):
			assert self.pan.num_channels == 1, "Pan modulators must be one channel signals"
			(pan,continue_flag) = self.pan.generate(frame_id,num_frames,sample_rate)
			pan = pan/2+.5

		else:
			pan = self.pan

		(data,continue_flag) = self.generator.generate(frame_id,num_frames,sample_rate)

		if not continue_flag:
			self.remove_generator()

		if self.generator.num_channels == 2:
			print("balancing")
			data.resize((len(data)//2,2))
			balance = (pan-.5)*2
			if balance > 0:
				balance = (1-balance,1)
			elif balance < 0:
				balance = (1,1-balance)
			else:
				balance = (1,1)
			return (data*balance).flatten()

		elif self.generator.num_channels == 1:
			return np.stack(((1-pan)*data,pan*data),axis=1).flatten()
		else:
			raise ValueError("Pan for " + self.generator.num_channels + " channel not implemented")

	def __generate__(self,frame_id,num_frames,sample_rate):
		return self.pan_func(frame_id,num_frames,sample_rate)


class StereoTrack(UnitGenerator):
	def __init__(self,mixer = Mixer(),pan = .5):
		
		super().__init__()
		self.num_channels = 2
		self.mixer = mixer
		self.panner = Panner(self.mixer,pan)

	def generate(self,frame_id,num_frames,sample_rate):
		return self.panner.generate(frame_id,num_frames,sample_rate)
		
