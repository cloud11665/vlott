#!/bin/env hy

(import os
        [textwrap [dedent]]
        [typing :as t])

(import uvicorn)
(import [fastapi [FastAPI Path Query]]
        [fastapi.middleware.cors [CORSMiddleware :as cors-middleware]]
        [fastapi.middleware.gzip [GZipMiddleware :as gzip-middleware]])

(import schemas
        [functions [get-timetable-data get-substitution-data]]
        [helpers [cached-lut json-obj-response json-str-response |||]])

(setv app (FastAPI))
(app.add-middleware cors-middleware
  :allow-credentials True
  :allow-origins ["*"]
  :allow-methods ["*"]
  :allow-headers ["*"])
(app.add-middleware gzip-middleware
  :minimum-size (<< 1 10))


(with-decorator (app.get "/vlo/listclass" :tags ["VLO"]
                 :response-model (of t.List str))
  (defn/a listclass []
    "
    Returns a sorted array of `str` representing every class in the timetable.\n
    Response model: `List[str]`
    "
    ;(print (cached-lut))
    (setv vals (-> (cached-lut)
                   (get "class" "id")
                   (.values)
                   (list)))
    (-> (lfor val vals
              (get val (slice 2 None)))
        (sorted)
        (json-obj-response))))

(with-decorator (app.get "/vlo/timestamps" :tags ["VLO"]
                 :response-model (of t.Dict str schemas.TimeIndex))
  (defn/a timestamps []
    "
    Returns a dictionary of `TimeIndex` objects, which are used for indexing the timetable.\n
    Response model: `Dict[str, TimeIndex]`
    "
    (-> (cached-lut)
        (get "time" "data")
        (json-obj-response))))

(with-decorator (app.get "/vlo/ttdata/{class_id}" :tags ["VLO"]
                 :response-model (of t.List (of t.List (of t.List schemas.Lesson))))
  (defn/a ttdata [&optional
                 ^schemas.ClassID [class-id (Path |||
                                   :description "The ID of class.")]
                 ^(of t.Optional int) [offset (Query 0 :ge -5 :le 5
                                       :description "Positive time offset in weeks.")]
                 ^(of t.Optional str) [default-color (Query "#D0FFD0"
                                       :description "Change the default color for lessons without predefined value.")]
                 ^(of t.Optional str) [override-color (Query None
                                       :description "Override every color in the timetable.")]]
    "
    Returns a 5 element array consisting of arrays representing concurrent lesons represented as an array of `Lesson` objects.\n
    Response model: `List[List[List[Lesson]]]`\n
    Cache timeout - 6h
    "
    (-> (get-timetable-data class-id.value offset default-color override-color :json? True)
        (json-str-response))))

(with-decorator (app.get "/vlo/substitutions/{class_id}" :tags ["VLO"]
                 :response-model (of t.List schemas.Substitution))
  (defn/a substitutions [&optional
                 ^schemas.ClassID [class-id (Path |||
                                   :description "The ID of class.")]
                 ^(of t.Optional int) [offset (Query 0 :ge -255 :le 255
                                       :description "Positive time offset in days.")]]
    "
    Returns an array of `Substitution` objects.\n
    Response model: `List[Substitution]`\n
    Cache timeout - 1h
    "
    (-> (get-substitution-data class-id.value offset :json? True)
        (json-str-response))))


(defmain [...]
  (if-not (os.system "grep -i 'microsoft' /proc/version >/dev/null 2>&1")
          (exit (dedent "\
                         Run it using a real operating system...
                         Exiting.")))
  (uvicorn.run app
               :port 7002
               :log-level "debug"
;               :workers 2
;               :worker_class "uvicorn.workers.UvicornH11Worker"
;               :timeout 30
;               :keepalive 2
               ))

