import wave
import numpy as np
from .unitgenerator import UnitGenerator

# Simple call to get_frames() to get data in format we like (numpy array, float32)
class WaveFile(object):
    def __init__(self, filepath) :
        super(WaveFile, self).__init__()

        self.wave = wave.open(filepath)
        self.num_channels, self.sampwidth, self.sr, self.end, \
           comptype, compname = self.wave.getparams()

        # for now, we will only accept 16 bit files at 44k
        assert(self.sampwidth == 2)
        assert(self.sr == 44100)

    # read an arbitrary chunk of data from the file
    def get_frames(self, start_frame, end_frame) :
        # get the raw data from wave file as a byte string. If asking for more than is available, it just
        # returns what it can
        self.wave.setpos(start_frame)
        raw_bytes = self.wave.readframes(end_frame - start_frame)

        # convert raw data to numpy array, assuming int16 arrangement
        samples = np.fromstring(raw_bytes, dtype = np.int16)

        # convert from integer type to floating point, and scale to [-1, 1]
        samples = samples.astype(np.float32)
        samples *= (1 / 32768.0)

        return samples

    def get_num_channels(self):
        return self.num_channels

        # generates audio data by asking an audio-source (ie, WaveFile) for that data.
class WaveGenerator(UnitGenerator):
    def __init__(self, wave_source, loop=False):
        super(WaveGenerator, self).__init__()
        self.source = wave_source
        self.num_channels = self.source.num_channels
        self.loop = loop
        self.paused = False
        self._release = False

    def reset(self):
        self.paused = True
        self.frame = 0

    def play_toggle(self):
        self.paused = not self.paused

    def play(self):
        self.paused = False

    def pause(self):
        self.paused = True

    def release(self):
        self._release = True

    def set_gain(self, g):
        self.gain = g

    def get_gain(self):
        return self.gain

    def  __generate__(self, frame_id,num_frames,sample_rate):
        if self.paused:
            output = np.zeros(num_frames * self.source.num_channels)
            return (output, True)

        else:
            # get data based on our position and requested # of frames
            output = self.source.get_frames(self.frame, self.frame + num_frames)
            # check for end-of-buffer condition:
            actual_num_frames = int(len(output) / self.num_channels)


            # looping. If we got to the end of the buffer, don't actually end.
            # Instead, read some more from the beginning

            shortfall = num_frames * self.num_channels - len(output)
            if self.loop and not shortfall>0:
                remainder = num_frames - actual_num_frames
                output = np.append(output, self.source.get_frames(0, remainder))
                self.frame = remainder

            # zero-pad if output is too short (may happen if not looping / end of buffer)
            shortfall = num_frames * self.num_channels - len(output)
            if shortfall > 0:
                output = np.append(output, np.zeros(shortfall))
                self.frame=0

            # return
            return output



class SpeedModulator(object):
    def __init__(self, generator, speed = 1.0):
        super(SpeedModulator, self).__init__()
        self.generator = generator
        self.speed = speed

    def set_speed(self, speed) :
        self.speed = speed

    def generate(self, num_frames, num_channels) :
        # optimization if speed is 1.0
        if self.speed == 1.0:
            return self.generator.generate(num_frames, num_channels)

        # otherwise, we need to ask self.generator for a number of frames that is
        # larger or smaller than num_frames, depending on self.speed
        adj_frames = int(round(num_frames * self.speed))

        # get data from generator
        data, continue_flag = self.generator.generate(adj_frames, num_channels)

        # split into multi-channels:
        data_chans = [ data[n::num_channels] for n in range(num_channels) ]

        # stretch or squash data to fit exactly into num_frames
        from_range = np.arange(adj_frames)
        to_range = np.arange(num_frames) * (float(adj_frames) / num_frames)
        resampled = [ np.interp(to_range, from_range, data_chans[n]) for n in range(num_channels) ]

        # convert back by interleaving into a single buffer
        output = np.empty(num_channels * num_frames, dtype=np.float32)
        for n in range(num_channels) :
            output[n::num_channels] = resampled[n]

        return (output, continue_flag)


# We can generalize the thing that WaveFile does - it provides arbitrary wave
# data. We can define a "wave data providing interface" (called WaveSource)
# if it can support the function:
#
# get_frames(self, start_frame, end_frame)
#
# Now create WaveBuffer. Same WaveSource interface, but can take a subset of
# audio data from a wave file and holds all that data in memory.
class WaveBuffer(object):
    def __init__(self, filepath, start_frame, num_frames):
        super(WaveBuffer, self).__init__()

        # get a local copy of the audio data from WaveFile
        wr = WaveFile(filepath)
        self.data = wr.get_frames(start_frame, start_frame + num_frames)
        self.num_channels = wr.get_num_channels()

    # start and end args are in units of frames,
    # so take into account num_channels when accessing sample data
    def get_frames(self, start_frame, end_frame) :
        start_sample = start_frame * self.num_channels
        end_sample = end_frame * self.num_channels
        return self.data[start_sample : end_sample]

    def get_num_channels(self):
        return self.num_channels