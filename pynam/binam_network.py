# -*- coding: utf-8 -*-

#   PyNAM -- Python Neural Associative Memory Simulator and Evaluator
#   Copyright (C) 2015 Andreas Stöckel
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Contains the Network class which is responsible for translating the BiNAM into
a spiking neural network.
"""

import binam
import binam_utils
import bisect
import itertools
import numpy as np
import pynnless as pynl
import pynnless.pynnless_utils as utils

class InputParameters(dict):
    """
    Contains parameters which concern the generation of input data.
    """

    def __init__(self, data={}, burst_size=1, time_window=100.0, isi=1.0,
            sigma_t=0.0, sigma_t_offs=0.0):
        utils.init_key(self, data, "burst_size", burst_size)
        utils.init_key(self, data, "time_window", time_window)
        utils.init_key(self, data, "isi", isi)
        utils.init_key(self, data, "sigma_t", sigma_t)
        utils.init_key(self, data, "sigma_t_offs", sigma_t_offs)

    def build_spike_train(self, offs=0.0):
        res = np.zeros(self["burst_size"])

        # Draw the actual spike offset
        if (self["sigma_t_offs"] > 0):
            offs = np.random.normal(offs, self["sigma_t_offs"])

        # Calculate the time of each spike
        for i in xrange(self["burst_size"]):
            jitter = 0
            if (self["sigma_t"] > 0):
                jitter = np.random.normal(0, self["sigma_t"])
            res[i] = offs + i * self["isi"] + jitter
        return np.sort(res)


class TopologyParameters(dict):
    """
    Contains parameters which concern the network topology -- the neuron type,
    the neuron multiplicity, neuron parameters and neuron parameter noise.
    """

    def __init__(self, data={}, params={}, param_noise={}, multiplicity=1,
            neuron_type=pynl.TYPE_IF_COND_EXP, w=0.03, sigma_w=0.0):
        """
        Constructor of the TopologyParameters class.

        :param data: is a dictionary from which the arguments are copied
        preferably.
        :param params: dictionary containing the neuron parameters.
        :param param_noise: dictionary potentially containing a standard
        deviation for each parameter.
        :param multiplicity: number of neurons and signals each component is
        represented with.
        :param neuron_type: PyNNLess neuron type name.
        :param w: synapse weight
        :param sigma_w: synapse weight standard deviation.
        """
        utils.init_key(self, data, "params", params)
        utils.init_key(self, data, "param_noise", param_noise)
        utils.init_key(self, data, "multiplicity", multiplicity)
        utils.init_key(self, data, "neuron_type", neuron_type)
        utils.init_key(self, data, "w", w)
        utils.init_key(self, data, "sigma_w", sigma_w)

        self["params"] = pynl.PyNNLess.merge_default_parameters(
                self["params"], self["neuron_type"])

    def draw(self):
        res = dict(self["params"])
        for key in res.keys():
            if key in self["param_noise"] and self["param_noise"][key] > 0:
                res["key"] = np.random.normal(res["key"],
                        self["param_noise"][key])
        return pynl.PyNNLess.clamp_parameters(res)

    def draw_weight(self):
        if self["sigma_w"] <= 0.0:
            return self["w"]
        return max(0.0, np.random.normal(self["w"], self["sigma_w"]))


class NetworkBuilder:

    # Number of samples
    N = 0

    # Input dimensionality
    m = 0

    # Output dimensionality
    n = 0

    # Input data matrix
    mat_in = None

    # Output data matrix
    mat_out = None

    # Internally cached BiNAM instance
    mem = None

    # Last sample until which the BiNAM has been trained
    last_k = 0

    def __init__(self, mat_in, mat_out):
        """
        Constructor of the NetworkBuilder class -- the NetworkBuilder collects
        information about a network (storage matrix, noise parameters and input
        data).

        :param mat_in: Nxm matrix containing the input data
        :param mat_out: Nxn matrix containing the output data
        :param s: neuron multiplicity
        """
        self.mat_in = mat_in
        self.mat_out = mat_out

        assert(mat_in.shape[0] == mat_out.shape[0])
        self.N = mat_in.shape[0]
        self.m = mat_in.shape[1]
        self.n = mat_out.shape[1]

    def build_topology(self, k=-1, seed=None, topology_params={}):
        """
        Builds a network for a BiNAM that has been trained up to the k'th sample
        """

        # If k is smaller than zero, use the number of samples instead
        if k < 0 or k > self.N:
            k = self.N

        # Train the BiNAM from the last trained sample last_k up to k
        if self.mem == None or self.last_k > k:
            self.mem = binam.BiNAM(self.m, self.n)
        for l in xrange(self.last_k, k):
            self.mem.train(self.mat_in[l], self.mat_out[l])
        self.last_k = k

        # Build input and output neurons
        t = TopologyParameters(topology_params)
        s = t["multiplicity"]
        net = pynl.Network()
        for i in xrange(self.m):
            for j in xrange(s):
                net.add_source()
        for i in xrange(self.n):
            for j in xrange(s):
                net.add_neuron(params=t.draw(), _type=t["neuron_type"],
                        record=pynl.SIG_SPIKES)

        def in_coord(i, k=1):
            return (i * s + k, 0)

        def out_coord(j, k=1):
            return (self.m * s + j * s + k, 0)

        # Add all connections
        for i in xrange(self.m):
            for j in xrange(self.n):
                if self.mem[i, j] != 0:
                    net.add_connections([
                        (in_coord(i, k), out_coord(j, l), t.draw_weight(), 0.0)
                        for k in xrange(s) for l in xrange(s)])
        return net

    def build_input(self, k=-1, time_offs=0, topology_params={},
            input_params={}, input_params_delay=10):
        """
        Builds the input spike trains for the network with the given input
        parameter sets. Returns a list with spike times for each neuron as first
        return value and a similar list containing the sample index for each
        spike time. Note that input_params may be an array of parameter sets --
        in this case multiple input spike trains are created.
        """

        # If k is smaller than zero, use the number of samples instead
        if k < 0 or k > self.N:
            k = self.N

        # Make sure mat_in is a numpy array
        if isinstance(self.mat_in, binam.BinaryMatrix):
            X = self.mat_in.get()
        else:
            X = np.array(self.mat_in, dtype=np.uint8)

        # Fetch the multiplicity s from the topology parameters
        s = TopologyParameters(topology_params)["multiplicity"]

        # Calculate the total maximum number of input spikes ovar all input
        # parameter sets
        max_num_spikes = 0
        if not isinstance(input_params, list):
            input_params = [input_params]
        for ip in input_params:
            p = InputParameters(ip)
            b = p["burst_size"]
            max_num_spikes = max_num_spikes + np.max(np.sum(X, 0)) * b

        # Create continuous two-dimensional target matrices
        T = np.zeros((s * self.m, max_num_spikes))
        K = np.zeros((s * self.m, max_num_spikes), dtype=np.int32)
        N = np.zeros(self.m, dtype=np.uint32)

        # Handle all input parameter sets
        t = 0
        sIdx = 0
        min_t = np.inf
        for ip in input_params:
            p = InputParameters(ip)
            b = p["burst_size"]

            # Calculate the maximum number of spikes, create two two-dimensional
            # matrix which contain the spike times and the sample indics
            for l in xrange(k):
                for i in xrange(self.m):
                    if X[l, i] != 0:
                        for j in xrange(s):
                            train = p.build_spike_train(t)
                            min_t = np.min([min_t, np.min(train)])
                            T[i * s + j, (N[i]):(N[i] + b)] = train
                            K[i * s + j, (N[i]):(N[i] + b)] = sIdx
                        N[i] = N[i] + b
                sIdx = sIdx + 1
                t = t + p["time_window"]
            t = t + p["time_window"] * input_params_delay

        # Offset the first spike time to time_offs
        T = T - min_t + time_offs

        # Extract a list of times and indices for each neuron
        input_times = [[] for _ in xrange(s * self.m)]
        input_indices = [[] for _ in xrange(s * self.m)]
        for i in xrange(self.m):
            for j in xrange(s):
                x = i * s + j
                I = np.argsort(T[x, 0:N[i]])
                input_times[x] = T[x, I].tolist()
                input_indices[x] = K[x, I].tolist()

        # Sample indices at which new input parameter sets start
        input_split = range(k, k * (len(input_params) + 1), k)

        return input_times, input_indices, input_split

    def inject_input(self, topology, times):
        """
        Injects the given spike times into the network.
        """
        for i in xrange(len(times)):
            topology["populations"][i]["params"]["spike_times"] = times[i]
        return topology

    def build(self, k=-1, time_offs=0, topology_params={}, input_params={}):
        """
        Builds a network with the given topology and input data that is ready
        to be handed of to PyNNLess.
        """
        topology = self.build_topology(k, topology_params=topology_params)
        input_times, input_indices, input_split = self.build_input(k,
                time_offs=time_offs,
                topology_params=topology_params,
                input_params=input_params)
        return NetworkInstance(
                self.inject_input(topology, input_times),
                input_times=input_times,
                input_indices=input_indices,
                input_split=input_split)

class NetworkInstance(dict):
    """
    Concrete instance of a BiNAM network that can be passed to the PyNNLess run
    method. A NetworkInstance can contain a time multiplex of simulations
    (with different input parameters). It provides a build_analysis method which
    splits the time multiplexed results into individual NetworkAnalysis objects.
    """

    def __init__(self, data={}, populations=[], connections=[],
            input_times=[], input_indices=[], input_split=[]):
        utils.init_key(self, data, "populations", populations)
        utils.init_key(self, data, "connections", connections)
        utils.init_key(self, data, "input_times", input_times)
        utils.init_key(self, data, "input_indices", input_indices)
        utils.init_key(self, data, "input_split", input_split)

    @staticmethod
    def flaten(times, indices, sort_by_sample=False):
        """
        Flatens a list of spike times and corresponding indices to three
        one-dimensional arrays containing the spike time, sample indices and
        neuron indices.
        """

        # Calculate the total count of spikes
        count = reduce(lambda x, y: x + y, map(len, times))

        # Initialize the flat arrays containing the times, indices and neuron
        # indices
        tF = np.zeros(count)
        kF = np.zeros(count, dtype=np.int32)
        nF = np.zeros(count, dtype=np.int32)

        # Iterate over all neurons and all spike times
        c = 0
        for i in xrange(len(times)):
            for j in xrange(len(times[i])):
                tF[c] = times[i][j]
                kF[c] = indices[i][j]
                nF[c] = i
                c = c + 1

        # Sort the arrays by spike time or sample
        if sort_by_sample:
            I = np.lexsort((kF, tF))
        else:
            I = np.argsort(tF)
        tF = tF[I]
        kF = kF[I]
        nF = nF[I]
        return tF, kF, nF

    @staticmethod
    def match_static(input_times, input_indices, output):
        """
        Extracts the output spike times from the simulation output and
        calculates the sample index for each output spike.
        """

        # Flaten and sort the input times and input indices for efficient search
        tIn, kIn, _ = NetworkInstance.flaten(input_times, input_indices)

        # Build the output times
        input_count = len(input_times)
        output_count = len(output) - input_count
        output_times = [[] for _ in xrange(output_count)]
        for i in xrange(output_count):
            output_times[i] = output[i + input_count]["spikes"][0]

        # Build the output indices
        output_indices = [[] for _ in xrange(output_count)]
        for i in xrange(output_count):
            output_indices[i] = [0 for _ in xrange(len(output_times[i]))]
            for j in xrange(len(output_times[i])):
                t = output_times[i][j]
                idx = bisect.bisect_left(tIn, t)
                if idx > 0:
                    idx = idx - 1
                if idx < len(tIn):
                    output_indices[i][j] = kIn[idx]

        return output_times, output_indices

    def match(self, output):
        """
        Extracts the output spike times from the simulation output and
        calculates the sample index for each output spike.
        """

        return self.match_static(self["input_times"], self["input_indices"],
                output)

    @staticmethod
    def split(times, indices, k0, k1):
        times_part = [[] for _ in xrange(len(times))]
        indices_part = [[] for _ in xrange(len(indices))]
        for i in xrange(len(times)):
            for j in xrange(len(times[i])):
                if indices[i][j] >= k0 and indices[i][j] < k1:
                    times_part[i].append(times[i][j])
                    indices_part[i].append(indices[i][j] - k0)
        return times_part, indices_part

    @staticmethod
    def build_analysis_static(input_times, input_indices, output,
            input_split=[]):
        # Fetch the output times and output indices
        output_times, output_indices = NetworkInstance.match_static(input_times,
                input_indices, output)

        # Only assume a single split if no input_split descriptor is given
        if (len(input_split) == 0):
            input_split = [max(map(max, input_indices)) + 1]

        # Split input and output spikes according to the input_split map, create
        # a NetworkAnalysis instance for each split
        res = []
        k0 = 0
        for k in input_split:
            input_times_part, input_indices_part = NetworkInstance.split(
                    input_times, input_indices, k0, k)
            output_times_part, output_indices_part = NetworkInstance.split(
                    output_times, output_indices, k0, k)
            res.append(NetworkAnalysis(
                    input_times=input_times_part,
                    input_indices=input_indices_part,
                    output_times=output_times_part,
                    output_indices=output_indices_part))
            k0 = k
        return res

    def build_analysis(self, output):
        return self.build_analysis_static(self["input_times"],
                self["input_indices"], output, self["input_split"])

class NetworkPool(dict):
    """
    The NetworkPool represents a spatial multiplex of multiple networks. It
    allows to add an arbitrary count of NetworkInstance objects and provides
    a "build_analysis" method which splits the network output into individual
    NetworkAnalysis object for each time/spatial multiplex.
    """

    def __init__(self, data={}, populations=[], connections=[],
            input_times=[], input_indices=[], input_split=[], spatial_split=[]):
        utils.init_key(self, data, "populations", populations)
        utils.init_key(self, data, "connections", connections)
        utils.init_key(self, data, "input_times", input_times)
        utils.init_key(self, data, "input_indices", input_indices)
        utils.init_key(self, data, "input_split", input_split)
        utils.init_key(self, data, "spatial_split", spatial_split)

        # Fix things up in case a NetworkInstance was passed to the constructor
        if (len(self["spatial_split"]) == 0 and len(self["populations"]) > 0):
            self["input_split"] = [self["input_split"]]
            self["spatial_split"].append({
                    "population": len(self["populations"]),
                    "input": len(self["input_times"])
                });

    def add_network(self, network):
        """
        Adds a new NetworkInstance to the execution pool.
        """

        # Old population and connection count
        nP0 = len(self["populations"])
        nC0 = len(self["connections"])

        # Append the network to the pool network
        self["populations"] = self["populations"] + network["populations"]
        self["connections"] = self["connections"] + network["connections"]
        self["input_times"] = self["input_times"] + network["input_times"]
        self["input_indices"] = self["input_indices"] + network["input_indices"]
        self["input_split"].append(network["input_split"])

        # Add a "spatial_split" -- this allows to dissect the network into its
        # original parts after the result is available
        nP1 = len(self["populations"])
        nC1 = len(self["connections"])
        nI1 = len(self["input_times"])
        self["spatial_split"].append({"population": nP1, "input": nI1});

        # Adapt the connection population indices of the newly added connections
        for i in xrange(nC0, nC1):
            c = self["connections"][i]
            self["connections"][i] = ((c[0][0] + nP0, c[0][1]),
                (c[1][0] + nP0, c[1][1]), c[2], c[3])

    def add_networks(self, networks):
        """
        Adds a list of NetworkInstance instances to the execution pool.
        """
        for network in networks:
            self.add_network(network)

    def build_analysis(self, output):
        """
        Performs spatial and temporal demultiplexing of the conducted
        experiments.
        """

        # Iterate over each spatial split and gather the analysis instances
        res = []
        last_split = {"population": 0, "input": 0}
        for i, split in enumerate(self["spatial_split"]):
            # Split the input times and the input indices at the positions
            # stored in the split descriptor
            input_times = self["input_times"][
                    last_split["input"]:split["input"]]
            input_indices = self["input_indices"][
                    last_split["input"]:split["input"]]

            # Split the output for the stored population range
            output_part = output[last_split["population"]:split["population"]]

            # Find the input_split descriptor, use an empty descriptor if no
            # valid input_split descriptor was stored.
            input_split = []
            if (i < len(self["input_split"]) and
                    isinstance(self["input_split"][i], list)):
                input_split = self["input_split"][i]

            # Let the NetworkInstance class build the analysis instances. This
            # class is responsible for performing the temporal demultiplexing.
            res = res + NetworkInstance.build_analysis_static(input_times,
                input_indices, output_part, input_split)
            last_split = split
        return res

class NetworkAnalysis(dict):
    """
    Contains the input and output spikes gathered for a single test run.
    Provides methods for performing a storage capacity and latency analysis.
    """

    def __init__(self, data={}, input_times=[], input_indices=[],
            output_times=[], output_indices=[]):
        utils.init_key(self, data, "input_times", input_times)
        utils.init_key(self, data, "input_indices", input_indices)
        utils.init_key(self, data, "output_times", output_times)
        utils.init_key(self, data, "output_indices", output_indices)

    def calculate_latencies(self):
        """
        Calculates the latency of each sample for both an input and output spike
        is available. Returns a list of latency values with an entry for each
        sample. The latency for samples without a response is set to infinity.
        """

        # Flaten the input and output times and indices
        tIn, kIn, _ = NetworkInstance.flaten(self["input_times"],
                self["input_indices"], sort_by_sample=True)
        tOut, kOut, _ = NetworkInstance.flaten(self["output_times"],
                self["output_indices"], sort_by_sample=True)

        # Fetch the number of samples
        N = np.max(kIn) + 1
        res = np.zeros(N)

        # Calculate the latency for each sample
        for k in xrange(N):
            # Fetch index of the latest input and output spike time for sample k
            iInK = bisect.bisect_right(kIn, k) - 1
            iOutK = bisect.bisect_right(kOut, k) - 1

            # Make sure the returned values are valid and actually refer to the
            # current sample
            if (iInK < 0 or iOutK < 0 or kIn[iInK] != k or kOut[iOutK] != k):
                res[k] = np.inf
            else:
                res[k] = tOut[iOutK] - tIn[iInK]
        return res

    def calculate_output_matrix(self, topology_params={},
            output_burst_size = 1):
        """
        Calculates a matrix containing the actually calculated output samples.
        """

        # Flaten the output spike sample indices and neuron indices
        _, kOut, nOut = NetworkInstance.flaten(self["output_times"],
                self["output_indices"], sort_by_sample=True)

        # Fetch the neuron multiplicity
        s = TopologyParameters(topology_params)["multiplicity"]

        # Create the output matrix
        N = max(map(lambda ks: max(ks + [0]), self["input_indices"])) + 1
        n = len(self["output_indices"]) // s
        res = np.zeros((N, n))

        # Iterate over each sample
        for k in xrange(N):
            # Fetch the indices in the flat array corresponding to that sample
            i0 = bisect.bisect_left(kOut, k)
            i1 = bisect.bisect_right(kOut, k)

            # For each output spike increment the corresponding entry in the
            # output matrix
            for i in xrange(i0, i1):
                res[k, nOut[i] // s] = res[k, nOut[i] // s] + 1

        # Scale the result matrix according to the output_burst_size
        return res / float(output_burst_size)

    def calculate_storage_capactiy(self, mat_out_expected, n_out_ones,
            topology_params = {}, output_burst_size = 1):
        """
        Calculates the storage capacity of the BiNAM, given the expected output
        data and number of ones in the output. Returns the information, the
        output matrix and the error counts.
        """
        mat_out = self.calculate_output_matrix(
                topology_params=topology_params,
                output_burst_size=output_burst_size)
        N, n = mat_out.shape
        errs = binam_utils.calculate_errs(mat_out, mat_out_expected)
        I = binam_utils.entropy_hetero(errs, n, n_out_ones)
        return I, mat_out, errs
