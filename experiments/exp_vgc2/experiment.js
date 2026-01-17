// ugly global state to communicate between callbacks
let _STATE = {
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

    // let targetStimuli = await fetch("./assets/targets/targets.json");
    let targetStimuli = await fetch("/sampleStimuli/vgc")
    targetStimuli = await targetStimuli.json();
    console.log(targetStimuli);
    // let targetStimuli = [
    //     {
    //         img: "./assets/lh_hh_plinko_0000/img.jpg",
    //         recording: "./assets/lh_hh_plinko_0000/recording.mp4",
    //         filler: true,
    //     },
    // ];
    let fillerStimuli = await fetch("./assets/fillers/fillers.json");
    fillerStimuli = await fillerStimuli.json();

    let stimuli;
    if (_DEBUG) {
        stimuli = targetStimuli;
        // stimuli = fillerStimuli;
    } else {
        // take three random fillers first, then shuffle the targets with the rest of the fillers
        // console.log("target", targetStimuli);
        let shuffledFiller = jsPsych.randomization.shuffle(fillerStimuli);
        console.log("shuffledFiller", shuffledFiller);
        stimuli = shuffledFiller.slice(0, 3).concat(jsPsych.randomization.shuffle(
            targetStimuli.concat(shuffledFiller.slice(3)))
        );
        // stimuli = jsPsych.randomization.shuffle(targetStimuli.concat(fillerStimuli))
    }
    console.log("stimuli", stimuli);

    jsPsych.data.addProperties({
        subject_id: subject_id,
        study_id: study_id,
        session_id: session_id,
    });

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
        },
    };
    timeline.push(consent);

    const instructions = {
        type: jsPsychConditionalInstructions,
        pages: [
            `<p class='instructions'>
      In this experiment, you will complete a task that involves trying to predict the path of a ball as it falls through an obstacle course. In each scenario, you will be presented with a scene of a ball suspended in air, above several bumper obstacles. You will then be asked to predict exactly which bin the ball will land in by clicking a button. The bins are numbered 1-5, going from left to right.
      <br><br>
      Here is an example of a world you might see:
      </p>
      <img src=./assets/demo/img.jpg style='max-width:40%'>,
      `,
      `<p class='instructions'>
      You will receive points based on how accurate your predictions are - you will earn 10 points for choosing the correct bin, 5 points for clicking a bin that is close to the correct bin, and 0 points otherwise. Try it now - what bin do you think the ball will land in? The 'Next' button will not activate until you select the correct option.
      <div>
      <img src=./assets/demo/img_binlabels.jpg style='max-width:40%'>
      </div>
      <br>
      <div>
        <input type='radio' id='bin-1' name='prediction'>
        <label for='bin-1'>Bin 1&nbsp;&nbsp;&nbsp;&nbsp;</label>
        <input type='radio' id='bin-2' name='prediction'>
        <label for='bin-2'>Bin 2&nbsp;&nbsp;&nbsp;&nbsp;</label>
        <input type='radio' id='bin-3' name='prediction'>
        <label for='bin-3'>Bin 3&nbsp;&nbsp;&nbsp;&nbsp;</label>
        <input type='radio' id='bin-4' name='prediction'>
        <label for='bin-4'>Bin 4&nbsp;&nbsp;&nbsp;&nbsp;</label>
        <input type='radio' id='bin-5' name='prediction'>
        <label for='bin-5'>Bin 5</label>
      </div>
      </p>
      `,
            `
      <p class='instructions'>
      Good job! Here's how the ball actually fell through the scene:
      </p>
      <video id='demo' style='max-width:40vw'>
        <source src=./assets/demo/recording.mp4 />
      </video>
      `,
        `<p class='instructions'>
        You will see 25 scenarios in this game, and it should take roughly 20 minutes to complete. Press the 'Next' button to begin the experiment.
        </p>`,
        ],
        setup_fns: [
            undefined,
            () => {
                if (_DEBUG) {
                    return;
                }
                document.querySelector("#jspsych-instructions-next").disabled = true;
                let q = document.querySelector("#bin-2");

                q.addEventListener("change", () => {
                    console.log("checked", q.checked);
                    if (q.checked) {
                        document.querySelector("#jspsych-instructions-next").disabled = false;
                    }
                });

                let q1 = document.querySelector("#bin-1");
                let q3 = document.querySelector("#bin-3");
                let q4 = document.querySelector("#bin-4");
                let q5 = document.querySelector("#bin-5");
                [q1, q3, q4, q5].map((e) => {
                    e.addEventListener("change", () => {
                        document.querySelector("#jspsych-instructions-next").disabled = true;
                    });
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

                setTimeout(() => {
                    video.play();
                }, 1000)
            },
            undefined,
        ],
        show_clickable_nav: true,
    };
    timeline.push(instructions);

    let predictAndProbe = {
        timeline: [
            {
                type: jsPsychHtmlButtonResponse,
                stimulus: () => {
                    _STATE.delete = false;
                    return `
                    <img src=${jsPsych.timelineVariable(_STATE.delete ? "img_del" : "img")} />,
                    `;
                },
                choices: ["bin 1", "bin 2", "bin 3", "bin 4", "bin 5"],
                canvas_size: [602, 630],
                prompt: () => {
                    return `<p>
                Current points total: ${_STATE.cumulative_points}
                </p><p>
                Please mark which bin you think that the ball will end up at after dropping,<br />
                by clicking on the buttons below.
                </p>
                `;
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
                    data.true_goal_numeric = parseInt(data.true_goal.at(-1));
                    data.delete = _STATE.delete;

                    if (data.response == data.true_goal_numeric) {
                        _STATE.points = 10;
                    } else {
                        // _STATE.points = 0;
                        let diff = Math.abs(data.response - data.true_goal_numeric);
                        _STATE.points = diff == 1 ? 5 : 0;
                    }
                    _STATE.cumulative_points += _STATE.points;
                    data.points = _STATE.points;
                    let progress = jsPsych.getProgressBarCompleted();
                    jsPsych.setProgressBar(progress + 1 / n_trials);
                    console.log(data);
                },
                css_classes: ["prediction-button"],
            },
            {
                type: jsPsychHtmlButtonResponse,
                stimulus: () => {
                    return `
                    <p>
                    You scored ${_STATE.points} points! The experiment will automatically proceed to the next page after a brief delay.
                    </p>
                    `;
                },
                choices: [],
                trial_duration: 2000,
                on_finish: (data) => {
                    // data.points = _STATE.points;
                    // _STATE.points = 0;
                },
                data: {
                    type: "show_points",
                },
            },
            {
                timeline: [
                    {
                        // type: jsPsychHtmlButtonResponse,
                        type: jsPsychHtmlSliderResponse,
                        stimulus: () => {
                            let probe_type = jsPsych.timelineVariable("probetype");

                            _STATE.base = jsPsych.timelineVariable("base_probe");
                            _STATE.distractor = jsPsych.timelineVariable(
                                "distractor_probe"
                            );
                            console.log("base_probe", _STATE.base);
                            console.log("distractor_probe", _STATE.distractor);
                            console.log("probing", probe_type);

                            return `
              <p>
              Pop quiz: below is the world that you just made predictions for, with two highlighted objects colored blue or red.
              One of these objects is the original object in its original position, and the other is a copy of that object that has been shifted to a new position.
              <br><br>
              Which object is in the <b>correct, original</b> position?
              <br><br>
              Please select a choice using the slider below. The 'Next' button will become enabled after you have touched the slider.
              </p>
              <div id='img-wrapper' style='display:flex;flex-wrap:nowrap;padding-bottom:5vh;position:relative'>
              <div id='centerer' style='display:flex;margin:auto;position:relative'>
              <img src=${_STATE.base} style='opacity:.35;z-index:1'>
              <img src=${_STATE.distractor} style='position:absolute;top:0;left:0;opacity:.5'>
              </div>
              </div>
              `;
                        },
                        on_finish: (data) => {
                            // data.answer = _STATE.answer;
                            // data.img = _STATE.probe_img;
                            console.log(data);
                        },
                        data: () => {
                            let out = {};
                            for (let key in targetStimuli[0]) {
                                out[key] = jsPsych.timelineVariable(key);
                            }
                            out.type = "probe";
                            return out;
                        },
                        // choices: ["red", "blue"],
                        labels: [
                            "Sure that the red object is in the original position",
                            "Not sure at all",
                            "Sure that the blue object is in the original position",
                        ],
                        require_movement: true,
                        css_classes: "slider-width",
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
                    let video = jsPsych.timelineVariable(_STATE.delete ? "recording_del" : "recording");
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
      compensation for this study: CT0HJL1O`;
            fetch("/saveData", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            }).then((res) => {
                console.log(res);
                if ((res.response = 200)) {
                    window.location.replace("https://app.prolific.com/submissions/complete?cc=CT0HJL1O");
                }
            });
        },
    };
    timeline.push(debrief);

    jsPsych.run(timeline);
    console.log(jsPsych.data.get());
}

main().catch((err) => console.log(err));
