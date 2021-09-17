#!/bin/env hy
(import json
        [hashlib [md5]])

(import [pymemcache.client [base]]
        [pymemcache.serde [pickle_serde :as pickle-serde]])

(defn str-md5 [^str input]
  (-> input
      (.encode)
      md5
      (.hexdigest)
      (cut 3)))

(setv client (.Client base ["127.0.0.1" 11211]
                           :serde pickle-serde))

(defclass --noneval []
  (defn --init-- [] pass))

(defn memcache [&optional ^int [ttl 0]]
  (defn outer [func]
    (defn inner [&rest args &kwargs kwargs]
       (setv arghash (-> (json.dumps [args kwargs] :sort_keys True :default str)
                         (str-md5)))
        (setv hname f"{--name--}{(name func)}_{arghash}")
        (setv ret (client.get hname --noneval))
        (if (= ret --noneval)
            (do (setv ret (func #* args #** kwargs))
                (client.set hname ret :expire ttl)))
      (return ret))
    (return inner))
  (return outer))

(setv client.cache memcache)