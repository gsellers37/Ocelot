import numpy as np
from .unitgenerator import UnitGenerator

class Oscillator(UnitGenerator):
	def __init__(self,freq,phase = 0,duration=None,pitch_type = "freq"):
		super().__init__(duration=duration)
		if pitch_type == "freq":
			self.set_freq(freq)
		else:
			raise ValueError("Invalid freq type to ", self.__class__, " object")

		self.phase = phase/180*np.pi
		self.last_angle = self.phase

	def set_freq(self,f):
		self.freq = f

	def oscillatorFunc(self,T,frames):
		raise ValueError(self.__class__ +" object does not have its oscillatorFunc specified")

	def __generate__(self,frame_id,num_frames,sample_rate):
		if isinstance(self.freq,UnitGenerator):
			[freq,cont] = self.freq.generate(frame_id,num_frames,sample_rate)
		else:
			freq = np.ones(num_frames)*self.freq
		if isinstance(self.phase,UnitGenerator):
			[phase,cont] = self.phase.generate(frame_id,num_frames,sample_rate)
		else:
			phase = self.phase
		omega = 2*np.pi*freq/sample_rate
		angle = self.last_angle + np.cumsum(omega) + phase
		self.last_angle = angle[-1]
		return self.oscillatorFunc(angle)

class SineGen(Oscillator):
	def __init__(self,freq,phase = 0,duration=None,pitch_type = "freq"):
		super().__init__(freq,phase=phase,duration=duration,pitch_type=pitch_type)

	def oscillatorFunc(self,angle):
		return np.sin(angle)