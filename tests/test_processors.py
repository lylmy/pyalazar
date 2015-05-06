import alazar.processor as proc
from alazar.processor import ProcessorException
from alazar.board import _AcqParams

from nose.tools import raises

import numpy as np

# some fake but realistic acquisition parameters
def acq_params():

    dtype = np.uint8

    return _AcqParams(samples_per_record=1024,
                      records_per_acquisition=128,
                      records_per_buffer=64,
                      channel_count=2,
                      dtype=dtype)

# make a bunch of test buffers with the same value
def buffers_same_val(params, value):
    bufs = [[np.full((params.records_per_buffer, params.samples_per_record),
                     value,
                     dtype=params.dtype,)
             for _ in range(params.channel_count)]
            for _ in range(params.buffers_per_acquisition)]
    return bufs

def buffers_random(params, min_val, max_val, seed=0):
    # seed the random number generator with a constant value
    np.random.seed(seed)
    bufs = [[(np.random.rand(params.records_per_buffer,
                             params.samples_per_record)*(max_val-min_val)+min_val
             ).astype(params.dtype)
             for _ in range(params.channel_count)]
            for _ in range(params.buffers_per_acquisition)]
    return bufs

# --- Automatic tests for various basic functions of all processors ---

class TestAllProcessors(object):

    def _setup_all_procs(self):
        # make a list of all the types of processors
        processors = []
        processors.append(proc.BufferProcessor())
        processors.append(proc.Average())
        processors.append(proc.Raw())
        processors.append(proc.AverageN(1))
        processors.append(proc.Chunk(proc.ChunkParam(0,1)))

        return processors

    def test_abort(self):
        for processor in self._setup_all_procs():
            yield (self.check_abort, processor)

    @raises(ProcessorException)
    def check_abort(self, processor):
        processor.abort(Exception())
        processor.get_result()

# --- tests for Average processor

class TestAverage(object):

    def test_process(self):
        ave = proc.Average()
        params = acq_params()
        ave.initialize(params)

        bufs = buffers_same_val(params, 1)

        run_process(bufs, ave)

        ave.post_process()

        dat = ave.get_result()

        for chan in range(params.channel_count):
            assert (bufs[chan][0] == dat[chan]).all()

        # test re-use of same processor with re-initializtion

        ave.initialize(params)

        # use randomized buffers this time
        bufs = buffers_random(params, 0, 255)

        raw_dat = bufs_to_raw_array(bufs, params)

        chan_aves = [np.mean(chan_dat,axis=0) for chan_dat in raw_dat]

        run_process(bufs, ave)

        ave.post_process()

        dat = ave.get_result()

        for chan in range(params.channel_count):

            assert (chan_aves[chan] == dat[chan]).all()

# --- tests for Raw processor

class TestRaw(object):

    def test_process(self):
        raw = proc.Raw()
        params = acq_params()
        raw.initialize(params)

        bufs = buffers_random(params, 0, 255)

        raw_dat = bufs_to_raw_array(bufs, params)

        run_process(bufs, raw)

        raw.post_process()

        dat = raw.get_result()

        for chan in range(params.channel_count):
            assert (raw_dat[chan] == dat[chan]).all()

# --- tests for AverageN processor

class TestAverageN(object):

    @raises(ProcessorException)
    def test_total_records_not_divisible_by_n(self):

        params = acq_params()
        assert params.records_per_acquisition % 3 != 0

        ave_N = proc.AverageN(3)
        ave_N.initialize(params)

        bufs = buffers_same_val(params, 1)

        run_process(bufs, ave_N)

        ave_N.post_process()
        ave_N.get_result()

    @raises(ProcessorException)
    def test_zero_n(self):
        ave_N = proc.AverageN(0)

    @raises(ProcessorException)
    def test_negative_n(self):
        ave_N = proc.AverageN(-1)

    def test_process(self):
        n_vals = [1,2,16]

        for val in n_vals:
            yield self.check_process_for_n_val, val

    def check_process_for_n_val(self, n_val):

        ave_n = proc.AverageN(n_val)

        params = acq_params()

        ave_n.initialize(params)

        bufs = buffers_random(params, 0, 255)

        raw_dat = bufs_to_raw_array(bufs, params)

        correct_results = [np.empty((n_val, params.samples_per_record), np.float)
                           for _ in range(params.channel_count)]

        # make the correct averaged data
        for rec_type in range(n_val):
            for result, chan_dat in zip(correct_results, raw_dat):
                result[rec_type] = np.mean(chan_dat[rec_type::n_val],axis=0)

        run_process(bufs, ave_n)

        ave_n.post_process()

        result = ave_n.get_result()

        for (correct, returned) in zip(correct_results, result):
            print correct[0,0]
            print returned[0,0]
            assert (correct == returned).all()

class TestChunk(object):

    @raises(ProcessorException)
    def test_total_records_not_divisible_by_n(self):
        params = acq_params()
        assert params.records_per_acquisition % 3 != 0

        chunk = proc.Chunk(0,1)
        chunk.initialize(params)

        bufs = buffers_same_val(params, 1)

        run_process(bufs, ave_N)

        chunk.post_process()
        chunk.get_result()



# --- Helper functions

def bufs_to_raw_array(bufs, params):

    raw_dat = [np.empty((params.records_per_acquisition, params.samples_per_record),
                        dtype=params.dtype) for _ in range(params.channel_count)]

    for (buf, buf_num) in zip(bufs,
                              range(params.buffers_per_acquisition)):

        for chan in range(params.channel_count):
            rec_p_buf = params.records_per_buffer
            raw_dat[chan][buf_num*rec_p_buf:(buf_num+1)*rec_p_buf][:] = buf[chan]

    return raw_dat

def run_process(bufs, procs):
    """Run this processor on all of these buffers.

    procs can be a single processor or a list of processors.
    """
    for (buf, buf_num) in zip(bufs,
                              range(len(bufs))):
        if type(procs) is list:
            for processor in procs:
                processor.process(buf, buf_num)
        else:
            procs.process(buf, buf_num)









