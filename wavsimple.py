# write (mono) wav file from samples, straight to file
# https://ccrma.stanford.edu/courses/422-winter-2014/projects/WaveFormat/
import struct

class wav:
    
    ChunkID             = b'RIFF'
    Format              = b'WAVE'
    SubChunk1ID         = b'fmt '
    AudioFormat         = 1 # PCM
    NumChannels         = 1 # mono, for the moment
    SubChunk1Size       = 16 # for PCM - size of chunk, not sample
    SubChunk2ID         = b'data'
    __fmt_hdr1          = '4s'
    __fmt_ChunkSize     = 'L'
    __idx_ChunkSize     = struct.calcsize(__fmt_hdr1)
    __fmt_hdr2          = '4s4sLHHLLHH4s'
    __fmt_SubChunk2Size = 'L'
    __idx_SubChunk2Size = struct.calcsize(__fmt_hdr1 + __fmt_ChunkSize + __fmt_hdr2)
    __fmt_hdr           = __fmt_hdr1 + __fmt_SubChunk2Size + __fmt_hdr2 + __fmt_SubChunk2Size

    # Silently overwrite existing file
    # SampleRate, BitsPerSample, NumChannels must be ints
    # BitsPerSample%8 must = 0
    def __init__(self, filename, SampleRate=12_000, BitsPerSample=8):
        """Create a new wav file with no samples"""
        self.filename = filename
        self.SampleRate = SampleRate
        self.BlockAlign = self.NumChannels * (BitsPerSample//8)
        self.ByteRate = SampleRate * self.BlockAlign
        self.BitsPerSample = BitsPerSample
        self.BlockCount = 0
        self.file = open(self.filename,'wb')
        self.file.write(self.__get_hdr())

    def SubChunk2Size(self):
        return len(self) * self.BlockAlign
    
    def ChunkSize(self):
        return 36 + self.SubChunk2Size()

    def __get_hdr(self):
        return struct.pack(
            self.__fmt_hdr,
            self.ChunkID,
            self.ChunkSize(),
            self.Format,
            self.SubChunk1ID,
            self.SubChunk1Size,
            self.AudioFormat,
            self.NumChannels,
            self.SampleRate,
            self.ByteRate,
            self.BlockAlign,
            self.BitsPerSample,
            self.SubChunk2ID,
            self.SubChunk2Size()
        )

    def write(self, samples):
        b = self.file.write(samples)
        self.BlockCount += b//self.BlockAlign
    
    def close(self):
        # update header file
        self.file.seek(self.__idx_ChunkSize)
        self.file.write(struct.pack(self.__fmt_ChunkSize, self.ChunkSize()))
        self.file.seek(self.__idx_SubChunk2Size)
        self.file.write(struct.pack(self.__fmt_SubChunk2Size, self.SubChunk2Size()))
        self.file.close()

    def __len__(self):
        return self.BlockCount
