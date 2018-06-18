import numpy as np
from .unitgenerator import UnitGenerator

class Envelope(UnitGenerator):
	def __init__(self,envelope,interp = "linear",find_next_point = None):
		super().__init__()
		self.num_channels = 1
		self.set_envelope(envelope)
		self.set_interpolation(interp)
		self.set_find_next_point(find_next_point)

	def set_envelope(self,env):
		if type(env) is list or type(env) is tuple:
			env = np.array(env)
		if type(env) is np.ndarray:
			if len(env.shape) is not 2 or env.shape[1] != 2 or env.shape[0] < 1:
				raise TypeError("Envelope needs to be an X by 2 array, where X is greater than 1.")
		else:
			raise TypeError("Envelope is not of proper type.")
		if env[0][0] != 0:
			np.concatenate(([[0,0]],env),axis=0)
		self.envelope = env

	def set_find_next_point(self,find_next_point):
		self.find_next_point = find_next_point

	def extend_envelope(self):
		if self.find_next_point:
			point = self.find_next_point(self.envelope[-1])
		else:
			raise RuntimeError("Trying to extend envelope with no defined find_next_point function.")
		self.envelope = np.concatenate((self.envelope,[point]),axis=0)

	def set_interpolation(self,interp_type):
		if interp_type == "linear":
			self.interp = np.interp
		if interp_type == "log":
			self.interp = self.log_interp

	def log_interp(self,t,x,y):
		logy = np.log10(y)

		return np.power(10.0,np.interp(t,x,logy))

	def __generate__(self,frame_id,num_frames,sample_rate):
		frames = np.arange(self.frame,self.frame+num_frames)/sample_rate
		if frames[-1] > self.envelope[-1,0]:
			self.extend_envelope()
		return self.interp(frames,self.envelope[:,0],self.envelope[:,1])
