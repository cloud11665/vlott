#!/bin/env hy
(import [enum [Enum]])

(import [pydantic [BaseModel]])

(import [helpers [cached-lut]])

(setv ClassID (Enum "ClassID"
                    (dfor x (lfor val (-> (cached-lut)
                                          (get "class" "id")
                                          (.values)
                                          (list))
                                  (get val (slice 2 None)))
                          [x x])))

(defclass Lesson [BaseModel]
  (setv ^str subject None
        ^str subject-short None
        ^str teacher None
        ^str classroom None
        ^str color None
        ^int time-index None
        ^int duration None
        ^str group None
        ^str date None
        ^int day-index None
        ^bool removed None))

(defclass TimeIndex [BaseModel]
  (setv ^str begin None
        ^str end None))

(defclass Substitution [BaseModel]
  (setv ^str time-signature None
        ^str comment None))
