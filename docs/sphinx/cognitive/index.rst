======================
Cognitive Architecture
======================

SomaBrain's cognitive modules emulate brain structures for AI agent processing.

.. toctree::
   :maxdepth: 2
   :caption: Core Structures

   amygdala
   hippocampus
   prefrontal
   thalamus
   basal-ganglia

.. toctree::
   :maxdepth: 2
   :caption: Memory Systems

   working-memory
   memory-client
   consolidation

.. toctree::
   :maxdepth: 2
   :caption: Computation

   quantum
   sdr
   prediction

Overview
========

SomaBrain implements a biologically-inspired cognitive architecture:

.. list-table:: Cognitive Modules
   :widths: 25 75
   :header-rows: 1

   * - Module
     - Function
   * - ``amygdala.py``
     - Emotional processing, salience detection
   * - ``hippocampus.py``
     - Memory formation, spatial mapping
   * - ``prefrontal.py``
     - Executive function, planning
   * - ``thalamus.py``
     - Sensory relay, attention gating
   * - ``basal_ganglia.py``
     - Motor control, habit formation
   * - ``wm.py``
     - Working memory (22KB)
   * - ``quantum.py``
     - Quantum operations (16KB)
   * - ``sdr.py``
     - Sparse distributed representations

Mathematical Foundations
========================

.. math::

   SDR_{active} = \{i : h_i > \theta, i \in [1, N]\}

Where :math:`h_i` is the activation of neuron :math:`i` and :math:`\theta` is the threshold.
