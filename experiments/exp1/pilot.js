// ugly global state to communicate between callbacks
let _STATE = { clickPositions: [], clickTimes: [], answer: 0, points: 0, cumulative_points: 0 }
let _DEBUG = true // don't show filler trials

async function main() {
  const jsPsych = initJsPsych({
    // on_finish: () => {
    //   jsPsych.data.displayData()
    // },
    show_progress_bar: true,
    auto_update_progress_bar: false,
  })
  let timeline = []

  let subject_id = jsPsych.data.getURLVariable('PROLIFIC_PID')
  let study_id = jsPsych.data.getURLVariable('STUDY_ID')
  let session_id = jsPsych.data.getURLVariable('SESSION_ID')

  jsPsych.data.addProperties({
    subject_id: subject_id,
    study_id: study_id,
    session_id: session_id
  })

  let targetStimuli = await fetch("sampleStimuli")
  targetStimuli = await targetStimuli.json()
  // console.log(targetStimuli)

  let fillerStimuli = await fetch("./assets/fillers.json")
  fillerStimuli = await fillerStimuli.json()
  // console.log(fillerStimuli)

  let catchStimuli = await fetch("./assets/catch.json")
  catchStimuli = await catchStimuli.json()
  // console.log(catchStimuli)

  let stimuli
  // stimuli = jsPsych.randomization.shuffle(targetStimuli.concat(fillerStimuli))
  if (_DEBUG) {
    stimuli = targetStimuli;
  } else {
    stimuli = jsPsych.randomization.shuffle(
      targetStimuli.concat(fillerStimuli).concat(catchStimuli)
    )
  }
  // console.log(stimuli)

  // stimuli = [{img: "../assets/tmp.jpg", filler: true, sim_x_result: 250, catch: false}]
  let n_trials = stimuli.length

  const consent = {
    type: jsPsychExternalHtml,
    url: "consent.html",
    cont_btn: "start",
    check_fn: (elem) => {
      if (_DEBUG) {
        return true
      }
      let eighteen = document.getElementById("eighteen-yes")
      let consent = document.getElementById("consent-yes")
      let understood = document.getElementById("understood-yes")

      return eighteen.checked && consent.checked && understood.checked
    },
  }
  timeline.push(consent)

  const welcomeMessage = {
    type: jsPsychHtmlButtonResponse,
    stimulus:
      "Welcome to the experiment! Press press the 'Next' button to begin.",
    choices: ["Next"],
  };
  timeline.push(welcomeMessage)

  const instructions = {
    type: jsPsychInstructions,
    pages: [
      `<p>
      In this experiment, you will complete a physical reasoning task that involves trying to predict the path of a ball as it falls through an obstacle course. In each scenario, you will be presented with a scene of a ball suspended in air, above several bumper obstacles. You will then be asked to predict exactly where the ball will hit the ground, by clicking on positions where you think the ball will land. You will receive point based on how accurate your predictions are - you may earn up to 10 points for each prediction you make, adding up to a total of 100 possible points on each scenario. Therefore, on scenarios where you may not be sure of where the ball ends up, you may want to spread out your clicks to maximize the points you earn. You will see 42 scenarios in this game, and it should take roughly 30 minutes to complete. On the next page, you will see an example of the kind of scene that you will be asked to make predictions about.
      </p>`,
      `<p>
      This video shows an example of how the ball might fall through the obstacles. On the next page, you will see how to make predictions about where the ball will land.
      </p>
      <video controls autoplay>
      <source src='assets/demo.mp4'>
      </video>`,
      `<p>
      Here is an example of the prediction task that you will be asked to complete. You will be asked to mark the spots you think that the ball will end up by clicking on the green area. You must click ten times to provide a range of places where you think the ball will land. These clicks will only register in the green area, and once you have indicated all ten places, you will see how the ball would actually fall.
      If you are uncertain about where the ball will go, we would like you to reflect that in the spread of your predictions - for example, in the video below, it might be unclear whether the ball would bounce left or right at the beginning, and so half of the clicks were on the left side, and the other half were on the right side. On the other hand, if you want to indicate certainty about where the ball will land, you can click the same or similar positions multiple times, like how there are a few clicks right next to each other in the video.
      </p>
      <video controls autoplay>
      <source src='assets/demo1.mp4'>
      </video>
      `,
      `<p>
      Press the 'Next' button to begin the experiment.
      </p>`
    ],
    show_clickable_nav: true,
  };
  timeline.push(instructions)

  let preload = {
    type: jsPsychPreload,
    auto_preload: true,
    images: stimuli.map((elem) => elem.img).concat(targetStimuli.map((elem) => elem.baseImg).concat(targetStimuli.map((elem) => elem.modifiedImg))),
    video: stimuli.map((elem) => elem.recording)
  }
  timeline.push(preload)

  let predictAndProbe = {
    timeline: [
      {
        type: jsPsychCanvasButtonResponse,
        stimulus: (c) => {
          let ctx = c.getContext("2d")
          let img = new Image()
          img.src = jsPsych.timelineVariable("img")
          img.onload = () => {
            ctx.drawImage(img, 0, 0)
          }
        },
        choices: _DEBUG ? ["next"] : [],
        canvas_size: [602, 630],
        prompt: () => {
          return `<p>
                Current points total: ${_STATE.cumulative_points}
                </p><p>
                Please click on the position that you think that the ball will end up at after dropping.
                Repeat this process 10 times - the screen will automatically go to the next page after the 10th
                click. You must click in the green area for the click to register.
                </p>
                `
        },
        on_load: () => {
          let c = document.getElementById("jspsych-canvas-stimulus")
          let ctx = c.getContext("2d")
          c.addEventListener("click", (e) => {
            let rect = c.getBoundingClientRect()
            if (e.clientY < rect.bottom - 75) {
              return
            }
            if (e.clientX > rect.left + 600) {
              // jspsych automatically tweaks the aspect ratio so that it is greater than 600px.
              // so, manually clamp all clicks to < 600
              return
            }
            let time = new Date().getTime()
            _STATE.clickTimes.push(
              time - _STATE.clickTimes.reduce((s, a) => s + a, 0)
            )
            let x = e.clientX - rect.left
            let y = rect.height - 10

            ctx.beginPath()
            ctx.arc(x, y - 5, 10, 0, 2 * Math.PI)
            ctx.fillStyle = "rgba(255, 0, 0, 0.7)"
            ctx.fill()
            _STATE.clickPositions.push(x)

            if (_STATE.clickPositions.length == 10) {
              _STATE.totalTime = new Date().getTime() - _STATE.trialBeginTime
              jsPsych.finishTrial()
            }
          })
          _STATE.trialBeginTime = new Date().getTime()
          _STATE.clickTimes.push(_STATE.trialBeginTime)
        },
        data: {
          filler: jsPsych.timelineVariable("filler"),
          img: jsPsych.timelineVariable("img"),
          catch: jsPsych.timelineVariable("catch"),
          true_x: jsPsych.timelineVariable("sim_x_result"),
          type: "prediction",
        },
        on_finish: (data) => {
          data.clickPositions = [..._STATE.clickPositions]
          _STATE.clickPositions = []
          data.clickTimes = [..._STATE.clickTimes.slice(1)]
          _STATE.clickTimes = []
          data.totalTime = _STATE.totalTime
          let progress = jsPsych.getProgressBarCompleted()
          jsPsych.setProgressBar(progress + 1 / n_trials)
        },
      },
      {
        type: jsPsychHtmlButtonResponse,
        stimulus: () => {
          let true_x = jsPsych.timelineVariable("sim_x_result")
          console.log(true_x)
          let out = []
          let clickPositions = jsPsych.data.getLastTrialData().trials[0].clickPositions
          console.log(clickPositions)
          for (let pos of clickPositions) {
            out.push(10 - Math.round((Math.abs(pos - true_x) / 60)))
          }
          console.log(out)
          let points = out.reduce((s, val) => s + val)
          _STATE.points = points
          _STATE.cumulative_points += points
          return `
          <p>
          You scored ${points} points! The experiment will automatically proceed to the next page after a brief delay.
          </p>
          `
        },
        choices: [],
        trial_duration: 2000,
        on_finish: (data) => {
          data.points = _STATE.points
          _STATE.points = 0
        },
        data: {
          type: "show_points",
        }
      },
      {
        timeline: [
          {
            type: jsPsychHtmlButtonResponse,
            stimulus: () => {
              let base = jsPsych.timelineVariable("baseImg")
              let modified = jsPsych.timelineVariable("modifiedImg")
              let left, right
              if (Math.random() < 0.5) {
                left = base;
                right = modified;
                _STATE.answer = 0;
              } else {
                left = modified;
                right = base;
                _STATE.answer = 1;
              }
              // return `
              // <p>
              // Pop quiz: in one of the two images below, the obstacle marked in red has changed shape. Which of the two images contains the obstacle you <b>actually</b> saw?
              // </p>
              // <div id='img-wrapper' style='display:flex;flex-wrap:nowrap;padding-bottom:5vh'>
              // <img src=${left} style='padding-right:10px;width:50%;height:auto'>
              // <img src=${right} style='padding-left:10px;width:50%;height:auto'>
              // </div>
              // `;
              return `
              <p>
              Pop quiz: in the below image, one of the highlighted shape was in the correct position, another was in the incorrect position. Which color object was in the <b>correct, original</b> position?
              </p>
              <div id='img-wrapper' style='display:flex;flex-wrap:nowrap;padding-bottom:5vh;position:relative'>
              <div id='centerer' style='display:flex;margin:auto;position:relative'>
              <img src=${left} style='opacity:.5'>
              <img src=${right} style='position:absolute;top:0;left:0;opacity:.5'>
              </div>
              </div>
              `;
            },
            on_finish: (data) => {
              data.answer = _STATE.answer;
            },
            data: {
              world: jsPsych.timelineVariable("world"),
              worldType: jsPsych.timelineVariable("worldType"),
              cond: jsPsych.timelineVariable("cond"),
              baseImg: jsPsych.timelineVariable("baseImg"),
              modifiedImg: jsPsych.timelineVariable("modifiedImg"),
              type: "probe",
            },
            choices: ["red", "blue"],
          },
        ],
        conditional_function: () => {
          let filler = jsPsych.timelineVariable("filler")
          return !filler
        },
      },
      {
        type: jsPsychHtmlButtonResponse,
        stimulus: () => {
          let video = jsPsych.timelineVariable("recording");
          return `
          <p>This following video shows how the ball would have actually fell.
          The 'Next' button will automatically pop up when the video stops playing.
          </p>
          <video controls id='feedback-video'>
          <source src=${video}>
          </video>`
        },
        on_load: () => {
          let button = document.getElementsByClassName("jspsych-btn")[0]
          button.style.visibility = "hidden"
          let video = document.getElementById("feedback-video")
          setTimeout(() => video.play(), 1000)
          video.addEventListener("ended", (e) => {
            button.style.visibility = "visible"
          })
        },
        data: {
          type: "feedback",
        },
        choices: ["Next"]
      },
    ],
    timeline_variables: stimuli,
  }
  timeline.push(predictAndProbe)

  let debrief = {
    type: jsPsychSurveyText,
    preamble: `
    Thank you for participating in our study. We would appreciate if you took the time to answer several questions
    about your experience. Please note that your answers to these questions will not impact your payment in any way - we simply
    wanted to get a sense of how people approached the task. So please be honest!

    Once you press the 'finish experiment' button,
    you will be directed back to the prolific in a few moments.
    `,
    questions: [
      {
        prompt: `On how many trials did you provide answers with little or no thought put into them
      (e.g. just providing an answer so you could move on to the next question)? Please enter a number.`,
      },
      { prompt: "Was there anything confusing or unclear about the study?" },
      { prompt: "Are there any additional comments you have for us?" },
    ],
    button_label: "finish experiment",
    on_finish: () => {
      let data = jsPsych.data.get().ignore("internal_node_id")
      console.log(data)
      document.body.innerHTML =
      `<p> Please wait. You will be redirected back to Prolific in a few moments.
      </p> If not, please use the following completion code to ensure \
      compensation for this study: C19G1QQB`
      fetch("/saveData", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      }).then((res) => {
        console.log(res)
        if ((res.response = 200)) {
          window.location.replace("https://app.prolific.co/submissions/complete?cc=C19G1QQB")
        }
      })
    },
  }
  timeline.push(debrief)

  jsPsych.run(timeline)
  console.log(jsPsych.data.get())
}

main().catch((err) => console.log(err));
