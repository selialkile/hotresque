# -*- coding: utf-8 -*-

"""Test suite for the HotResque library. To run this test suite, execute this
Python program (``python tests.py``). Redis must be running on localhost:6379,
and a list key named 'HotResque:testqueue' will be created and deleted in db 0
several times while the tests are running.
"""

from time import sleep
import threading
import unittest

from HotResque import HotResque


class HotResqueTestCase(unittest.TestCase):
    
    def setUp(self):
        """Create the queue instance before the test."""
        self.queue = HotResque('testqueue')
    
    def tearDown(self):
        """Clear the queue after the test."""
        self.queue.clear()
    
    def test_consume(self):
        """Test the consume generator method."""
        nums = [1, 2, 3, 4, 5, 6, 7, 8]
        # Test blocking with timeout:
        self.queue.put(*nums)
        msgs = []
        for msg in self.queue.consume(timeout=1):
            msgs.append(msg)
        self.assertEquals(msgs, nums)
        # Test non-blocking:
        self.queue.put(*nums)
        msgs = []
        for msg in self.queue.consume(block=False):
            msgs.append(msg)
        self.assertEquals(msgs, nums)
    
    def test_cleared(self):
        """Test for correct behaviour if the Redis list does not exist."""
        self.assertEquals(len(self.queue), 0)
        self.assertEquals(self.queue.get(), None)
    
    def test_get_order(self):
        """Test that messages are get in the same order they are put."""
        alphabet = ['abc', 'def', 'ghi', 'jkl', 'mno']
        self.queue.put(alphabet[0], alphabet[1], alphabet[2])
        self.queue.put(alphabet[3])
        self.queue.put(alphabet[4])
        msgs = []
        msgs.append(self.queue.get())
        msgs.append(self.queue.get())
        msgs.append(self.queue.get())
        msgs.append(self.queue.get())
        msgs.append(self.queue.get())
        self.assertEquals(msgs, alphabet)
    
    def test_length(self):
        """Test that the length of a queue is returned correctly."""
        self.queue.put('a message')
        self.queue.put('another message')
        self.assertEquals(len(self.queue), 2)
    
    def test_worker(self):
        """Test the worker decorator."""
        colors = ['blue', 'green', 'red', 'pink', 'black']
        # Test blocking with timeout:
        self.queue.put(*colors)
        msgs = []
        @self.queue.worker(timeout=1)
        def appender(msg):
            msgs.append(msg)
        appender()
        self.assertEqual(msgs, colors)
        # Test non-blocking:
        self.queue.put(*colors)
        msgs = []
        @self.queue.worker(block=False)
        def appender(msg):
            msgs.append(msg)
        appender()
        self.assertEqual(msgs, colors)
    
    def test_threaded(self):
        """Threaded test of put and consume methods."""
        msgs = []
        def put():
            for num in range(3):
                self.queue.put('message %d' % num)
                sleep(0.1)
        def consume():
            for msg in self.queue.consume(timeout=1):
                msgs.append(msg)
        putter = threading.Thread(target=put)
        consumer = threading.Thread(target=consume)
        putter.start()
        consumer.start()
        for thread in [putter, consumer]:
            thread.join()
        self.assertEqual(msgs, ['message 0', 'message 1', 'message 2'])


if __name__ == "__main__":
    unittest.main()

