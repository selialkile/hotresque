# -*- coding: utf-8 -*-

"""HotResque is a Python library that allows you to use Redis as a message queue
within your Python programs.
"""

from functools import wraps
try:
    import cPickle as pickle
except ImportError:
    import pickle

from redis import Redis
import json


__all__ = ['HotResque']

__version__ = '0.2.7'


def key_for_name(name):
    """Return the key name used to store the given queue name in Redis."""
    return '%s:%s' % (name_queue, name)


class HotResque(object):
    
    """Simple FIFO message queue stored in a Redis list. Example:

    >>> from HotResque import HotResque
    >>> queue = HotResque("myqueue", host="localhost", port=6379, db=0)
    
    :param name: name of the queue
    :param serializer: the class or module to serialize msgs with, must have
        methods or functions named ``dumps`` and ``loads``,
        `pickle <http://docs.python.org/library/pickle.html>`_ is the default,
        use ``None`` to store messages in plain text (suitable for strings,
        integers, etc)
    :param kwargs: additional kwargs to pass to :class:`Redis`, most commonly
        :attr:`host`, :attr:`port`, :attr:`db`

    ==============================================
    
    Para pegar uma migracao que está na fila

    >>> from hotresque import HotResque
    >>> a = HotResque("queue:migrations")
    >>> a.name_queue = "resque"
    >>> c = a.get() 

    o GET do hotresque retorna um dicionario contendo todos os dados.

    conteudo de "c"
    {
        u'port_dest': 443, 
        u'host_dest': u'destino.teste.com', 
        u'username_dest': None,
        u'password_dest': None, 
        u'migration_id': 9, 
        u'port_orig': 443, 
        u'password_orig': u'teste123', 
        u'host_orig': u'origem.teste.com', 
        u'username_orig': u'teste@teste.com'
     }

    >>> c['port_dest']
    443
    >>> c['username_dest']

    Para setar o status da migracao:

    >>> import json
    >>> from hotresque import HotResque
    >>> a = HotResque("queue:migrations_report")
    >>> a.name_queue = "resque"
    >>> resp = {"class":"MigrationReport", "args" : [json.dumps({"migration_id" : 5, "state":"ok|error" , "message":"mensagem..."}) ]}
    >>> a.put(resp)

    """
    
    def __init__(self, name, serializer=json, **kwargs):
        self.name = name
        self.serializer = serializer
        self.__redis = Redis(**kwargs)
        self.name_queue = "hotresque"
    
    def __len__(self):
        return self.__redis.llen(self.key)

    def name_queue():
        doc = "The name_queue property."
        def fget(self):
            return self._name_queue
        def fset(self, value):
            self._name_queue = value
        def fdel(self):
            del self._name_queue
        return locals()
    name_queue = property(**name_queue())
    
    @property
    def key(self):
        """Return the key name used to store this queue in Redis."""
        return '%s:%s' % (self.name_queue, self.name)
    
    def clear(self):
        """Clear the queue of all messages, deleting the Redis key."""
        self.__redis.delete(self.key)
    
    def consume(self, **kwargs):
        """Return a generator that yields whenever a message is waiting in the
        queue. Will block otherwise. Example:
        
        >>> for msg in queue.consume(timeout=1):
        ...     print msg
        my message
        another message
        
        :param kwargs: any arguments that :meth:`~HotResque.HotResque.get` can
            accept (:attr:`block` will default to ``True`` if not given)
        """
        kwargs.setdefault('block', True)
        try:
            while True:
                msg = self.get(**kwargs)
                if msg is None:
                    break
                yield msg
        except KeyboardInterrupt:
            print; return
    
    def get(self, block=False, timeout=None):
        """Return a message from the queue. Example:
    
        >>> queue.get()
        'my message'
        >>> queue.get()
        'another message'
        
        :param block: whether or not to wait until a msg is available in
            the queue before returning; ``False`` by default
        :param timeout: when using :attr:`block`, if no msg is available
            for :attr:`timeout` in seconds, give up and return ``None``
        """
        if block:
            if timeout is None:
                timeout = 0
            msg = self.__redis.blpop(self.key, timeout=timeout)
            if msg is not None:
                msg = msg[1]
        else:
            msg = self.__redis.lpop(self.key)
        if msg is not None and self.serializer is not None:
            msg = self.serializer.loads(msg)
            msg = json.loads(msg['args'][0])
        return msg
    
    def put(self, *msgs):
        """Put one or more messages onto the queue. Example:
        
        >>> queue.put("my message")
        >>> queue.put("another message")
        
        To put messages onto the queue in bulk, which can be significantly
        faster if you have a large number of messages:
        
        >>> queue.put("my message", "another message", "third message")
        """
        if self.serializer is not None:
            msgs = map(self.serializer.dumps, msgs)
        self.__redis.rpush(self.key, *msgs)
    
    def worker(self, *args, **kwargs):
        """Decorator for using a function as a queue worker. Example:
        
        >>> @queue.worker(timeout=1)
        ... def printer(msg):
        ...     print msg
        >>> printer()
        my message
        another message
        
        You can also use it without passing any keyword arguments:
        
        >>> @queue.worker
        ... def printer(msg):
        ...     print msg
        >>> printer()
        my message
        another message
        
        :param kwargs: any arguments that :meth:`~HotResque.HotResque.get` can
            accept (:attr:`block` will default to ``True`` if not given)
        """
        def decorator(worker):
            @wraps(worker)
            def wrapper(*args):
                for msg in self.consume(**kwargs):
                    worker(*args + (msg,))
            return wrapper
        if args:
            return decorator(*args)
        return decorator

