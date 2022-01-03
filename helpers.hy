#!/bin/env hy
(import [datetime [datetime timedelta]]
        json)

(import [fastapi [Response]]
        requests)

(import [cacheclient [client]])

(defn json-obj-response [data]
  (Response :content (json.dumps data :ensure_ascii False)
            :media-type "application/json"))

(defn json-str-response [data]
  (Response :content data
            :media-type "application/json"))

(setv ||| (eval "..."))

(with-decorator (client.cache (* 24 60 60))
  (defn cached-lut []
    (print "a")
    (setv today (datetime.today)
          year  today.year)
    (setv last-monday (+ today (timedelta :days (- (today.weekday))))
          next-friday (+ last-monday (timedelta :days 4)))

    (setv resp (requests.post
                :url "https://v-lo-krakow.edupage.org/rpr/server/maindbi.js?__func=mainDBIAccessor"
                :headers {
                  "User-Agent" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0"
                  "Referer" "https://v-lo-krakow.edupage.org/timetable"
                }
                :json {
                 "__args" [
                   None
                   2021
                   {
                     "vt_filter" {
                       "datefrom" (last-monday.strftime "%Y-%m-%d")
                       "dateto"   (next-friday.strftime "%Y-%m-%d")
                     }
                   }
                   {
                     "op" "fetch"
                     "tables"  []
                     "columns" []
                     "needed_part" {
                       "teachers" ["__name" "short"]
                       "classes"  ["__name" "classroomid"]
                       "classrooms" ["__name" "name" "short"]
                       "igroups"  ["__name"]
                       "students" ["__name" "classid"]
                       "subjects" ["__name" "name" "short"]
                       "events" ["typ" "name"]
                       "event_types"   ["name"]
                       "subst_absents" ["date" "absent_typeid" "groupname"]
                       "periods"  ["__name" "period" "starttime" "endtime"]
                       "dayparts" ["starttime" "endtime"]
                       "dates"  ["tt_num" "tt_day"]
                     }
                     "needed_combos" {}
                     "client_filter" {}
                     "info_tables"  []
                     "info_columns" []
                     "has_columns"  {}
                   }
                 ]
                 "__gsh" "00000000"
                }))
    (setv lut {
      "teachers" {
        "id" {"short" {} }
      }
      "subjects" {
        "id" {"short" {} "long" {} }
      }
      "class" {
        "room" {"id" {} }
        "idr" {}
        "id" {}
      }
      "time" {
        "data" {}
        "rmap" {}
        "map" {}
      }
    })

    (setv data (get (resp.json) "r"))
    (for [teacher (get data "tables" 0 "data_rows")]
      (setv [x y] (teacher.values))
      (setv (. lut["teachers"]["id"]["short"][x]) y))

    (for [subj (get data "tables" 1 "data_rows")]
      (setv [x y z] (subj.values))
      (setv (. lut["subjects"]["id"]["long"][x]) y
            (. lut["subjects"]["id"]["short"][x]) z))

    (for [room (get data "tables" 2 "data_rows")]
      (setv [x y] (room.values))
      (setv (. lut["class"]["room"]["id"][x]) y))

    (for [klass (get data "tables" 3 "data_rows")]
      (setv [x y _] (klass.values))
      (setv (. lut["class"]["id"][x]) y
            (. lut["class"]["idr"][y]) x))

    (for [time (get data "tables" 6 "data_rows")]
      (setv [x _ _ _ y z] (time.values))
      (setv (. lut["time"]["data"][x]) {"begin" y "end" z}
            (. lut["time"]["map"][y]) x
            (. lut["time"]["rmap"][x]) y))

    (return lut)))