// ugly global state to communicate between callbacks
let _STATE = {
    clickPositions: [],
    clickTimes: [],
    left: "",
    right: "",
    answer: 0,
    points: 0,
    cumulative_points: 0,
};
let _DEBUG = false;

async function main() {
    const jsPsych = initJsPsych({
        on_finish: () => {
            jsPsych.data.displayData();
        },
        show_progress_bar: true,
        auto_update_progress_bar: false,
    });

    if (jsPsych.data.getURLVariable("debug") !== undefined) {
        _DEBUG = jsPsych.data.getURLVariable("debug") == "true";
    }
    console.log("debug mode", _DEBUG);

    let timeline = [];

    let subject_id = jsPsych.data.getURLVariable("PROLIFIC_PID");
    let study_id = jsPsych.data.getURLVariable("STUDY_ID");
    let session_id = jsPsych.data.getURLVariable("SESSION_ID");

    let targetStimuli = await fetch("sampleStimuli/teleporter");
    targetStimuli = await targetStimuli.json();
    console.log(targetStimuli);

    let fillerStimuli = await fetch("./assets/fillers.json");
    fillerStimuli = Object.values(await fillerStimuli.json());

    fillerStimuli = jsPsych.randomization.shuffle(fillerStimuli);
    targetStimuli = jsPsych.randomization.shuffle(targetStimuli);
    console.log("fillers", fillerStimuli);

    fillerStimuli.forEach((element, idx) => {
        element.worldtype = Math.random() < 0.5 ? 1 : 2;
    });
    targetStimuli.forEach((element) => {
        element.worldtype = Math.random() < 0.5 ? 1 : 2;
    });

    let stimuli;
    // stimuli = jsPsych.randomization.shuffle(targetStimuli.concat(fillerStimuli))
    if (_DEBUG) {
        stimuli = targetStimuli;
    } else {
        stimuli = jsPsych.randomization.shuffle(targetStimuli.concat(fillerStimuli.slice(6)));
        stimuli = fillerStimuli.slice(0, 6).concat(stimuli);
    }
    console.log("stimuli", stimuli);

    let entry_color_idx = Math.round(Math.random());
    let teleporter_colors = ["brown", "blue"];

    let teleporter_entry_color = teleporter_colors[entry_color_idx];
    let teleporter_exit_color = teleporter_colors[1 - entry_color_idx];

    jsPsych.data.addProperties({
        teleporter_entry_color_idx: entry_color_idx,
        teleporter_entry_color: teleporter_colors[entry_color_idx],
        subject_id: subject_id,
        study_id: study_id,
        session_id: session_id,
    });

    // entry_color_idx = 1;
    // stimuli = [{img1_1: "assets/demo1_1.png", img1_2: "assets/demo1_2.png", img2_2: "assets/demo2_2.png", img2_1: "assets/demo2_1.png", filler: true, sim_x_result1: 250, worldtype: "1"}]
    let n_trials = stimuli.length;

    const consent = {
        type: jsPsychExternalHtml,
        url: "consent.html",
        cont_btn: "start",
        execute_script: !_DEBUG,
        check_fn: (elem) => {
            if (_DEBUG) {
                return true;
            }
            let eighteen = document.getElementById("eighteen-yes");
            let consent = document.getElementById("consent-yes");
            let understood = document.getElementById("understood-yes");

            return eighteen.checked && consent.checked && understood.checked;
        }
    };
    timeline.push(consent);

    const instructions = {
        type: jsPsychConditionalInstructions,
        pages: [
            `<p>
      In this experiment, you will complete a task that involves trying to predict the path of a ball as it falls through an obstacle course. In each scenario, you will be presented with a scene of a ball suspended in air, above several bumper obstacles. You will then be asked to predict exactly where the ball will hit the ground, by clicking on positions where you think the ball will land.
      <br><br>
      Here is an example of a world you might see. Notice that there are two circular objects colored brown and blue. <b>Pay special attention to these objects</b>: we will describe exactly what they do in the next few pages.
      </p>
      <img src=assets/demo1_${entry_color_idx+1}.png style='max-width:40%'>,
      `,
            `<p>
      You will receive points based on how accurate your predictions are - you may earn up to 10 points for each prediction you make, adding up to a total of 100 possible points on each scenario. Therefore, on scenarios where you may not be sure of where the ball ends up, you may want to spread out your clicks to maximize the points you earn.
      <br>
      <br>
      You will see 27 scenarios in this game, and it should take roughly 20 minutes to complete. On the next page, you will see an example of how a ball might fall through the scene.
      </p>`,
      `<p>
      The two circles are teleporters. <b>All ${teleporter_entry_color} circles are teleporter entrances, and all ${teleporter_exit_color} circles are teleporter exits.</b>

      So, when the ball falls through the teleporter entrance, it will be transported after a brief delay to the teleporter exit, with the same velocity and direction of movement.
      The example below shows an example of the teleporter in action. The ball falls through the ${teleporter_entry_color} teleporter entrance, and then appears at the ${teleporter_exit_color} teleporter exit, where it continues to fall. Click on the video to play it: the 'Next' button will become enabled after the video finishes.
      </p>
      <video controls id='demo' style='max-width:40vw'>
      <source src=assets/demo-recording1_${entry_color_idx+1}.mp4>
      </video>`,
      `
      <p>
      <b>NOTE</b>: The teleporter exit is a completely permeable object. So, any object will pass through it instead of bouncing off. In the video below, we've swapped the position of the teleporter entrance and exit, so that the exit is now below the ball. You can see that the ball passes through the teleporter exit as if it didn't exist.
      </p>

      <video controls id='demo' style='max-width:40vw'>
      <source src=assets/demo-recording2_${entry_color_idx+1}.mp4>
      </video>
      `,
            `<p>
      Here is an example of the prediction task that you will be asked to complete. You will be asked to mark the spots you think that the ball will end up by clicking on the green area. You must click ten times to provide a range of places where you think the ball will land. These clicks will only register in the green area, and once you have indicated all ten places, you will see how the ball would actually fall.
      </p>
      <video controls id='demo' style='max-width:35%'>
      <source src=assets/clickdemo${entry_color_idx+1}.mov>
      </video>
      <p>
      If you are uncertain about where the ball will go, we would like you to reflect that in the spread of your predictions - for example, in the video below, it might be unclear whether the ball would bounce left or right at the beginning, and so half of the clicks were on the left side, and the other half were on the right side.
      On the other hand, if you want to indicate certainty about where the ball will land, you can click the same or similar positions multiple times, like how there are a few clicks right next to each other in the video.
      </p>
      `,
      `<p>
      Here are some questions about the task that was just introduced. The 'next' button will activate once you have answered all the questions correctly.
      </p>
      <ul>
      <li>
      What color is the teleporter entrance?
      <div>
        <input type='radio' id='entrance-1' name='teleporter-entrance'>
        <label for='entrance-1'>Brown</label>
        <input type='radio' id='entrance-2' name='teleporter-entrance'>
        <label for='entrance-2'>Blue</label>
        <input type='radio' id='entrance-3' name='teleporter-entrance'>
        <label for='entrance-3'>Red</label>
        <input type='radio' id='entrance-4' name='teleporter-entrance'>
        <label for='entrance-4'>Green</label>
      </div>
      </li>
      <br>

      <li>
      If the ball falls onto the teleporter exit circle, what will happen?
      <div>
        <input type='radio' id='exit-1' name='teleporter-exit'>
        <label for='exit-1'>The ball will bounce off of the exit</label>
        <input type='radio' id='exit-2' name='teleporter-exit'>
        <label for='exit-2'>The ball will pass through the exit</label>
      </div>
      </li>
      <br>

      <li>
      What happens to the speed of the ball when the ball falls through the teleporter entrance and appears at the exit?
      <div>
        <input type='radio' id='effect-1' name='teleporter-effect'>
        <label for='effect-1'>The ball will retain the speed and motion that it had before entering the teleporter</label>
        <br>
        <input type='radio' id='effect-2' name='teleporter-effect'>
        <label for='effect-2'>The ball's motion will be reset, and will start from a standstill after exiting</label>
      </div>
      </li>
      </ul>
      `,
            `<p>
      Press the 'Next' button to begin the experiment.
      </p>`,
        ],
        setup_fns: [
            undefined,
            undefined,
            () => {
                if (_DEBUG) {
                    return;
                }
                document.querySelector("#jspsych-instructions-next").disabled = true;
                let video = document.querySelector("#demo");
                video.addEventListener("ended", () => {
                    document.querySelector("#jspsych-instructions-next").disabled = false;
                });
            },
            () => {
                if (_DEBUG) {
                    return;
                }
                document.querySelector("#jspsych-instructions-next").disabled = true;
                let video = document.querySelector("#demo");
                video.addEventListener("ended", () => {
                    document.querySelector("#jspsych-instructions-next").disabled = false;
                });
            },
            () => {
                if (_DEBUG) {
                    return;
                }
                document.querySelector("#jspsych-instructions-next").disabled = true;
                let video = document.querySelector("#demo");
                video.addEventListener("ended", () => {
                    document.querySelector("#jspsych-instructions-next").disabled = false;
                });
            },
            () => {
                if (_DEBUG) {
                    return;
                }
                document.querySelector("#jspsych-instructions-next").disabled = true;
                let q1 = document.querySelector(`#entrance-${entry_color_idx + 1}`);
                let q2 = document.querySelector("#exit-2");
                let q3 = document.querySelector("#effect-1");

                [q1, q2, q3].map((e) => {e.addEventListener("change", () => {
                    if (q1.checked && q2.checked && q3.checked) {
                        document.querySelector("#jspsych-instructions-next").disabled = false;
                    }
                })})
            }
        ],
        show_clickable_nav: true,
    };
    timeline.push(instructions);

    let predictAndProbe = {
        timeline: [
            {
                type: jsPsychCanvasButtonResponse,
                stimulus: (c) => {
                    let ctx = c.getContext("2d");
                    let img = new Image();
                    _STATE.img = jsPsych.timelineVariable("img" + jsPsych.timelineVariable("worldtype") + "_" + (entry_color_idx+1));
                    console.log("serving stimulus ", _STATE.img);
                    img.src = _STATE.img;
                    img.onload = () => {
                        ctx.drawImage(img, 0, 0);
                    };
                    _STATE.true_x = jsPsych.timelineVariable(
                        "sim_x_result" + jsPsych.timelineVariable("worldtype")
                    );
                },
                choices: _DEBUG ? ["next"] : [],
                canvas_size: [602, 630],
                prompt: () => {
                    return `<p>
                Current points total: ${_STATE.cumulative_points}
                </p><p>
                Please click on the position that you think that the ball will end up at after dropping.
                <b>Remember: the ${teleporter_entry_color} circle is a teleporter entrance, and the ${teleporter_exit_color} circle is a teleporter exit. the teleporter exit is not an object: the ball will simply fall through the teleporter exit as if it was not there.</b>
                Repeat this process 10 times - the screen will automatically go to the next page after the 10th
                click. You must click in the green area for the click to register.
                </p>
                `;
                },
                on_load: () => {
                    let c = document.getElementById("jspsych-canvas-stimulus");
                    let ctx = c.getContext("2d");
                    c.addEventListener("click", (e) => {
                        let rect = c.getBoundingClientRect();
                        if (e.clientY < rect.bottom - 75) {
                            return;
                        }
                        if (e.clientX > rect.left + 600) {
                            // jspsych automatically tweaks the aspect ratio so that it is greater than 600px.
                            // so, manually clamp all clicks to < 600
                            return;
                        }
                        let time = new Date().getTime();
                        _STATE.clickTimes.push(time - _STATE.clickTimes.reduce((s, a) => s + a, 0));
                        let x = e.clientX - rect.left;
                        let y = rect.height - 10;

                        ctx.beginPath();
                        ctx.arc(x, y - 5, 10, 0, 2 * Math.PI);
                        ctx.fillStyle = "rgba(255, 0, 0, 0.7)";
                        ctx.fill();
                        _STATE.clickPositions.push(x);

                        if (_STATE.clickPositions.length == 10) {
                            _STATE.totalTime = new Date().getTime() - _STATE.trialBeginTime;
                            jsPsych.finishTrial();
                        }
                    });
                    _STATE.trialBeginTime = new Date().getTime();
                    _STATE.clickTimes.push(_STATE.trialBeginTime);
                },
                data: () => {
                    let tmp = targetStimuli[0];
                    let out = {};
                    for (let key in tmp) {
                        out[key] = jsPsych.timelineVariable(key);
                    }
                    out.type = "prediction";
                    return out;
                },
                on_finish: (data) => {
                    data.true_x = _STATE.true_x;
                    data.img = _STATE.img;

                    data.clickPositions = [..._STATE.clickPositions];
                    _STATE.clickPositions = [];
                    data.clickTimes = [..._STATE.clickTimes.slice(1)];
                    _STATE.clickTimes = [];
                    data.totalTime = _STATE.totalTime;
                    let progress = jsPsych.getProgressBarCompleted();
                    jsPsych.setProgressBar(progress + 1 / n_trials);
                    console.log(data);
                },
            },
            {
                type: jsPsychHtmlButtonResponse,
                stimulus: () => {
                    let true_x = _STATE.true_x;
                    console.log(true_x);
                    let out = [];
                    let clickPositions = jsPsych.data.getLastTrialData().trials[0].clickPositions;
                    console.log(clickPositions);
                    for (let pos of clickPositions) {
                        out.push(10 - Math.abs(Math.round(pos / 60) - Math.round(true_x / 60)));
                    }
                    let points = 0;
                    if (out.length > 0) {
                        points = out.reduce((s, val) => s + val);
                    }
                    _STATE.points = points;
                    _STATE.cumulative_points += points;
                    return `
                    <p>
                    You scored ${points} points! The experiment will automatically proceed to the next page after a brief delay.
                    </p>
                    `;
                },
                choices: [],
                trial_duration: 2000,
                on_finish: (data) => {
                    data.points = _STATE.points;
                    _STATE.points = 0;
                },
                data: {
                    type: "show_points",
                },
            },
            {
                timeline: [
                    {
                        type: jsPsychHtmlSliderResponse,
                        stimulus: () => {
                            let probe_obj = ["nocol", "1", "2"][parseInt(jsPsych.timelineVariable("probe_obj_idx"))];
                            let world = jsPsych.timelineVariable("world");
                            let worldtype = jsPsych.timelineVariable("worldtype");

                            let stim_idx = worldtype == "1" ? entry_color_idx : 1 - entry_color_idx;
                            _STATE.img = `assets/targets/${world}/normstim_color${stim_idx}_${probe_obj}.png`;
                            _STATE.probe_obj = probe_obj;
                            console.log("probing", probe_obj);
                            console.log("img", _STATE.img);
                            return `
              <p style='margin:10%;margin-bottom:2%'>
              Pop quiz: below is the world that you just made predictions for. One object is colored red.
              <br>
              Please indicate how confident you are that the ball will hit the <b>red</b> object.
              <br>
              Select a choice using the slider below. The 'Next' button will become enabled after you have touched the slider.
              </p>
              <div id='img-wrapper' style='display:flex;flex-wrap:nowrap;padding-bottom:5vh;position:relative'>
              <div id='centerer' style='display:flex;margin:auto;position:relative;justify-content:center'>
              <img src=${_STATE.img} style='width:100%'/>
              </div>
              </div>
              `;
                        },
                        on_finish: (data) => {
                            data.img = _STATE.img;
                            data.probe_obj = _STATE.probe_obj;
                        },
                        data: () => {
                            let tmp = targetStimuli[0];
                            let out = {};
                            for (let key in tmp) {
                                out[key] = jsPsych.timelineVariable(key);
                            }
                            out.type = "norm";
                            return out;
                        },
                        // min: 1,
                        // max: 7,
                        // slider_start: 4,
                        labels: [
                            "Completely sure that the ball will not hit the object",
                            "Not sure at all",
                            "Completely sure that the ball will hit the object",
                        ],
                        require_movement: true,
                        // css_classes: "slider-width",
                        slider_width: 625,
                    },
                ],
                conditional_function: () => {
                    let filler = jsPsych.timelineVariable("filler");
                    return !filler;
                },
            },
            {
                type: jsPsychHtmlButtonResponse,
                stimulus: () => {
                    let video = jsPsych.timelineVariable("recording" + jsPsych.timelineVariable("worldtype") + "_" + (entry_color_idx+1));
                    return `
          <p>This following video shows how the ball would have actually fell.
          The "Next" will automatically show up once the video finishes.
          </p>
          <video id='feedback-video'>
          <source src=${video}>
          </video>`;
                },
                on_load: () => {
                    let button = document.getElementsByClassName("jspsych-btn")[0];
                    if (!_DEBUG) {
                        button.style.visibility = "hidden";
                    }
                    let video = document.getElementById("feedback-video");
                    setTimeout(() => video.play(), 1000);
                    video.addEventListener("ended", (e) => {
                        button.style.visibility = "visible";
                        // button.click();
                    });
                },
                data: {
                    type: "feedback",
                },
                choices: ["Next"],
            },
        ],
        timeline_variables: stimuli,
    };
    timeline.push(predictAndProbe);

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
            {
                prompt: "Was there anything confusing or unclear about the study?",
            },
            { prompt: "Are there any additional comments you have for us?" },
        ],
        button_label: "finish experiment",
        on_finish: () => {
            let data = jsPsych.data.get().ignore("internal_node_id");
            console.log(data);
            document.body.innerHTML = `<p> Please wait. You will be redirected back to Prolific in a few moments.
      </p> If not, please use the following completion code to ensure \
      compensation for this study: C19G1QQB`;
            fetch("/saveData", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            }).then((res) => {
                console.log(res);
                if ((res.response = 200)) {
                    window.location.replace("https://app.prolific.co/submissions/complete?cc=CT0HJL1O");
                }
            });
        },
    };
    timeline.push(debrief);

    jsPsych.run(timeline);
    console.log(jsPsych.data.get());
}

main().catch((err) => console.log(err));
