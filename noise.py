import numpy as np
from .unitgenerator import UnitGenerator

class NoiseGen(UnitGenerator):
	def __init__(self):
		super().__init__()

	def __generate__(self,frame_id,num_frames,sample_rate):
		return np.random.rand(self.num_channels*num_frames)