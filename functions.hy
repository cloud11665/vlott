#!/bin/env hy
(import [hy.contrib.pprint [pprint]])

(import [datetime [datetime timedelta
                   date :as ddate]]
        [itertools [groupby]]
        [typing :as t]
        re
        json
        random)

(import [lxml [html]]
        requests)

(import [cacheclient [client]]
        [helpers [cached-lut]])

(defn html-redo [x]
  (html.fromstring (html.tostring x)))

(defn html-x-expr [x ^str expr]
  (-> (html-redo x)
      (.xpath expr)))

(defn html-x-text [x ^str expr]
  (as-> (html-redo x) it
        (it.xpath expr)
        (.join "" it)))

(defn prep-teacher [^str teacher]
  (setv pat (re.compile r"_\w$"))
  (if (pat.findall teacher)
      (return f"{(last teacher)}. {(get teacher (slice -2))}"))
  (return teacher))

(defn prep-classroom [^str classroom]
  (cond [(= classroom "iinf3") (return "13B")]
        [(= classroom "inf4") (return "20")]
        [(= classroom "inf3") (return "13B")]
        [(= classroom "aeorbik") (return "aerobik")])
  (return classroom))

(defn prep-group [^str group]
  (setv pat1 (re.compile r"\d+$")
        num (->> (pat1.findall group)
                 (.join "")))
  (cond [(= group "wychowanie fizyczne_dz") (return "wf dziewczyny")]
        [(= group "wychowanie fizyczne_ch") (return "wf chłopcy")]
       ;[(and (group.startswith "język") num) (return f"język {num}")]
        [(in "_" group) (return (prep-group (group.replace "_" " ")))]
       ;[(group.startswith "język niemiecki") (return "")]
       ;[(group.startswith "język angielski") (return "")]
        [num (return f"{(get group (slice (- (len num))))} {num}")]
        )
  (return group))

(defn prep-subj [^str subj]
  (cond [(= subj "język francuski") (return "Język francuski")])
  (return subj))

(defn prep-subj-sh [^str subj]
  (cond [(= subj "fran") (return "J.francuski")]
        [(= subj "J.niemiecki") (return "j.niemiecki")]
        [(= subj "polski") (return "j.polski")])
  (return subj))

(with-decorator (client.cache (* 6 60 60))
  (defn get-timetable-data [^str klass &optional
                            ^int  [offset 0]
                            ^str  [default-color "#d0ffd0"]
                            ^(of t.Union str None) [override-color None]
                            ^bool [json? False]]
    (if-not (re.match r"^\d_\d\w+$" klass)
            (do (setv klass f"{(get klass 0)}_{klass}")))

    (setv lut (cached-lut))

    (setv today (ddate.today)
          now   (datetime.now))
    (setv week-offset (timedelta :weeks offset)
          last-monday (+ today (timedelta :days (- (today.weekday))) week-offset)
          next-friday (+ last_monday (timedelta :days 4)))

    (setv resp (requests.post
                :url "https://v-lo-krakow.edupage.org/timetable/server/currenttt.js?__func=curentttGetData"
                :headers {
                  "User-Agent" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0"
                  "Referer" "https://v-lo-krakow.edupage.org/timetable"
                }
                :json {
                  "__args" [
                     None
                     {
                       "year" 2021
                       "datefrom" (last-monday.strftime "%Y-%m-%d")
                       "dateto" (next-friday.strftime "%Y-%m-%d")
                       "id" (get lut "class" "idr" klass)
                       "showColors" True
                       "showIgroupsInClasses" True
                       "showOrig" True
                       "table" "classes"
                     }
                  ]
                  "__gsh" "00000000"
                }))
    (if-not resp.ok
            (return [[] [] [] [] []]))

    (setv raw-data (get (resp.json) "r" "ttitems")
          data [])

    (for [[idx obj] (enumerate raw-data)]
         (setv [year month day] (map int (-> obj (.["date"])
                                                 (.split "-"))))
         (as-> (ddate year month day) day-idx
               (- day-idx last-monday)
               day-idx.days)

         (if (and (< (int (-> (. obj["starttime"]) (.split ":") first)) ;;start hour < 7
                     7)
                  (> (int (-> (. obj["endtime"])   (.split ":") first)  ;;end hour > 17
                     17)))
             (setv (. obj["starttime"]) "07:10"
                   (. obj["endtime"])   "17:15"
                   (. obj["durationperiods"]) 11))

         (setv date      (obj.get "date")
               subj-id   (obj.get "subjectid" "0")
               color     (-> (obj.get "colors" [default-color])
                             first)
               subject   (-> (. lut["subjects"]["id"]["long"])
                             (.get subj-id "")
                             (prep-subj))
               subj-sh   (-> (. lut["subjects"]["id"]["short"])
                             (.get subj-id "")
                             (prep-subj-sh))
               time-idx  (-> (. lut["time"]["map"])
                             (.get (obj.get "starttime") "0")
                             int)
               duration  (-> (obj.get "durationperiods" 1)
                             int)
               group     (->> (obj.get "groupnames" [""])
                              (.join "")
                              (prep-group))
               teacher   (as-> (obj.get "teacherids" ["0"]) id
                               (.join "" id)
                               (-> (. lut["teachers"]["id"]["short"])
                                   (.get id "")
                                   (prep-teacher)))
               classroom (as-> (obj.get "classroomids" ["0"]) id
                               (.join "" id)
                               (-> (. lut["class"]["room"]["id"])
                                   (.get id "")
                                   (prep-classroom))))

         (if override-color
             (setv color override-color))

         (data.append {
           "subject"       subject
           "subject_short" subj-sh
           "teacher"       teacher
           "classroom"     classroom
           "color"         color
           "time_index"    time-idx
           "duration"      duration
           "group"         group
           "date"          date
           "day_index"     day-idx
         }))

    ;; for whatever reason edupage doesn't return sorted data
    (data.sort :key (fn [x] (get x "day_index")))

    (for [x data]
      (if (= (-> (get x "subject")
                 (.lower))
             "religia")
          (setv (. x["group"]) "religia 1")))

    (setv output [[] [] [] [] []])
    (setv days (dfor x data [(get x "day_index") []]))
    (for [x data]
      (.append (. days[(get x "day_index")]) x))

    (for [[idx day] (days.items)]
      (for [[x y] (groupby day (fn [x] (get x "time_index")))]
        (-> (. output[idx])
            (.append (list y)))))

    (if json?
        (return (json.dumps output
                            :ensure-ascii False)))
    (return output)))

(with-decorator (client.cache (* 6 60 60))
  (defn get-substitution-data [^str klass &optional
                               ^int [offset 0]
                               ^bool [json? False]]
  (if-not (re.match r"^\d_\d\w+$" klass)
          (do (setv klass f"{(get klass 0)}_{klass}")))

  (setv date-to (+ (datetime.today) (timedelta :days offset)))
  (setv resp (requests.post
              :url "https://v-lo-krakow.edupage.org/substitution/server/viewer.js?__func=getSubstViewerDayDataHtml"
              :headers {
                "User-Agent" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0"
                "Referer" "https://v-lo-krakow.edupage.org/substitution"
              }
              :json {
                "__args" [
                  None
                  {
                    "date" (date-to.strftime "%Y-%m-%d")
                    "mode" "classes"
                  }
                ]
                "__gsh" "00000000"
              }))


  (setv dom (html.fromstring (get (resp.json) "r")))
  (setv lc-translator "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'")
  (setv pat f"//div[@class = 'section print-nobreak'
                    and translate(./div[@class='header']/span/text(), {lc-translator}) = '{(klass.lower)}']")
  (setv query (dom.xpath pat))
  (setv output [])
  (if query
      (do (setv query (get query 0))
          (for [row (html-x-expr query "//div[./div[@class='period'] and ./div[@class='info']]")]
              (output.append {
                "comment" (html-x-text row "//div[@class='info']/span/text()")
                "time_signature" (html-x-text row "//div[@class='period']/span/text()")
              }))))
  (if json?
      (return (json.dumps output
                          :ensure-ascii False)))
  (return output)))
