import pyaudio
import numpy as np
import wave
import os

class AudioController(object):
	def __init__(self,num_channels,sample_rate,buffer_size,listener = None,generator = None):
		self.num_channels = num_channels
		self.sample_rate = sample_rate
		self.buffer_size = buffer_size

		self.listener = listener
		self.generator = generator

		#Initialize pyaudio parameters
		self.audio = pyaudio.PyAudio()
		self.stream = self.audio.open(format = pyaudio.paFloat32,
				 channels = self.num_channels,
				 rate = self.sample_rate,
				 frames_per_buffer = self.buffer_size,
				 output = True,
				 input = False)

		#Used to determine if unitgenerators should move on in their generation or regenerate the last set of frames
		self.frame_id = 0

		self.playing = False

	def set_generator(self,generator):
		self.generator = generator
		if self.generator.num_channels != self.num_channels:
			raise TypeError("Master output to AudioController does not have the same amount of channels")

	def remove_generator(self):
		self.generator = None

	def close(self):
		self.stream.stop_stream()
		self.stream.close()
		self.audio.close()

	def update(self):		
		num_frames = self.stream.get_write_available()
		if num_frames > 0:
			if self.generator:
				(data,continue_flag) = self.generator.generate(self.frame_id,num_frames,self.sample_rate)
				self.frame_id = (self.frame_id + 1) % 2
				if data.dtype != np.float32:
					data = data.astype(np.float32)
				self.stream.write(data.tostring())

				if self.listener:
					self.listener.add_audio(data, self.sample_rate,self.num_channels)
			else:
				raise ValueError("AudioController object has no generator to update.")

	def render(self,time,sample_rate,verbose = True):
		def print_progress(percentage):
			toolbar_width = 40
			progress = int((percentage*toolbar_width)%toolbar_width)
			strtowrite = "Render progress [%s%s] %f %% Complete" % ("%"*progress," " * (toolbar_width-progress), percentage*100)
			print(strtowrite,end='\r')

		if self.listener == None:
			raise ValueError("AudioController is not connected to a writer, and therefore cannot render.")

		self.listener.start()

		t=0		
		if verbose:
			print_progress(t/time)

		while(t<time):
		
			t+=1
			if self.generator:
				(data,continue_flag) = self.generator.generate(self.frame_id,sample_rate,self.sample_rate)
				self.frame_id = (self.frame_id + 1) % 2
				if data.dtype != np.float32:
					data = data.astype(np.float32)

				self.listener.add_audio(data, self.sample_rate,self.num_channels)
			if verbose:
				print_progress(t/time)

			else:
				raise ValueError("AudioController object has no generator to render.")
		print()
		self.listener.stop()
		print('Done rendering')

	def get_device(self,type):
		pass


	def print_devices(self):
		num_devices = self.audio.get_device_count()
		for i in range(num_devices):
			device_info = self.audio.get_device_info_by_index(i)
			print(device_info)

		num_apis = self.audio.get_host_api_count()
		print(num_apis)
		for i in range(num_apis):
			print(self.audio.get_host_api_info_by_index(i))

class AudioWriter(object):
	def __init__(self,num_channels, sample_rate, sample_width, filebase, output_type=".wav"):
		super(AudioWriter, self).__init__()

		self.active = False

		self.set_num_channels(num_channels)
		self.set_sample_rate(sample_rate)
		self.set_sample_width(sample_width)
		self.filebase = filebase

		self.write_filetype = {'.wav':self.wave_file_writer}
		self.set_output_type(output_type)



		
		self.buffers = []
		self.sample_rate = sample_rate


	def set_output_type(self,output_type):
		if self.active:
			raise RuntimeError("Cannot set the output filetype of the AudioWriter when the object is recording.")
		if output_type not in self.write_filetype:
			error_str = "The file type "+output_type+" is not currently supported by the AudioWriter class."
			raise ValueError(error_str)
		self.output_type = output_type

	def set_num_channels(self,num_channels):
		if self.active:
			raise RuntimeError("Cannot set number of channels of the AudioWriter when the object is recording.")
		if not( num_channels == 1 or num_channels == 2):
			raise ValueError("AudioWriter currently only supports mono and stereo recording") 
		self.num_channels = num_channels

	def set_sample_width(self,sample_width):
		if self.active:
			raise RuntimeError("Cannot set sample width of the AudioWriter when the object is recording.")
		if sample_width == 1:
			self.sample_type = np.int8
		elif sample_width == 2:
			self.sample_type = np.int16
		elif sample_width == 4:
			self.sample_type = np.int32
		else:
			raise ValueError("AudioWriter currently only supports bit depths of 8, 16, or 32 for recording")
		self.sample_width = sample_width

	def set_sample_rate(self,sample_rate):
		if self.active:
			raise RuntimeError("Cannot set sample width of the AudioWriter when the object is recording.")
		self.sample_rate = sample_rate

	def add_audio(self, data, sample_rate, num_channels) :
		if self.active:
			if sample_rate != self.sample_rate:
				raise ValueError("Source audio and AudioWriter do not share the same samplerate. Changing sample rates is currently not supported by the AudioWriter class.")
			# Downsample stereo to mono
			if num_channels == 2 and self.num_channels == 1:
				data = (data[0::2]+data[1::2])/2

			# Upsample mono to stereo
			if num_channels == 1 and self.num_channels == 2:
				data = np.array(list(zip(data,data)),dtype=data.dtype).flatten()

			self.buffers.append(data)

	def toggle(self) :
		if self.active:
			self.stop()
		else:
			self.start()

	def start(self) :
		if not self.active:
			print('AudioWriter: starting to record audio stream')
			self.active = True
			self.buffers = []

	def stop(self) :
		if self.active:
			print('AudioWriter: stoped recording audio stream')
			self.active = False

			output = self.combine_buffers()
			if len(output) == 0:
				print('AudioWriter: empty buffers. Nothing to write')
				return

			self.write_file(output)

	def write_file(self,output):
		filename = self._get_filename()
		print('AudioWriter: saving', len(output), 'samples in', filename)
		self.write_filetype[self.output_type](output,filename)

	# look for a filename that does not exist yet.
	def _get_filename(self) :
		suffix = 0
		while(True) :
			if suffix == 0:
				filename = '%s%s' % (self.filebase, self.output_type)
			else:
				filename = '%s%d%s' % (self.filebase, suffix, self.output_type)
			if not os.path.exists(filename) :
				return filename
			else:
				response = input("Filename " + filename + " already exists, would you like to overwrite? (y/n)")
				if response == 'y':
					return filename
				else:
					suffix += 1


	# create single buffer from an array of buffers:
	def combine_buffers(self):
		size = 0
		for b in self.buffers:
			size += len(b)

		# create a single output buffer of the right size
		output = np.empty( size, dtype=np.float32 )
		f = 0
		for b in self.buffers:
			output[f:f+len(b)] = b
			f += len(b)
		return output


	def wave_file_writer(self,buf, name):
		f = wave.open(name, 'w')
		f.setnchannels(self.num_channels)
		f.setsampwidth(self.sample_width)
		f.setframerate(self.sample_rate)

		buf = buf*(2**(8*self.sample_width-1)-.5)-.5
		buf = buf.astype(self.sample_type)
		f.writeframes(buf.tostring())