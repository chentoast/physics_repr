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
    let timeline = [];

    let subject_id = jsPsych.data.getURLVariable("PROLIFIC_PID");
    let study_id = jsPsych.data.getURLVariable("STUDY_ID");
    let session_id = jsPsych.data.getURLVariable("SESSION_ID");

    let targetStimuli = await fetch("sampleStimuli/bg");
    targetStimuli = await targetStimuli.json();
    // console.log(targetStimuli)

    let fillerStimuli = await fetch("./assets/fillers.json");
    fillerStimuli = Object.values(await fillerStimuli.json());

    // let catchStimuli = await fetch("./assets/catch.json");
    // catchStimuli = await catchStimuli.json();
    // console.log(catchStimuli)

    let stimuli = targetStimuli;
    if (_DEBUG) {
        stimuli = targetStimuli;
    } else {
        stimuli = jsPsych.randomization.shuffle(targetStimuli.concat(fillerStimuli));
    }
    // stimuli = [{ baseImg0: "assets/demo/demo2/world_0.jpg", baseImg1: "assets/demo/demo2/world_1.jpg", filler: true, sim_x_result: 250 }]
    console.log(stimuli);

    let background_color_idx = Math.round(Math.random());
    // let background_color_idx = 1;
    let background_colors = ["brown", "blue"];

    jsPsych.data.addProperties({
        background_color_idx: background_color_idx,
        background_color: background_colors[background_color_idx],
        subject_id: subject_id,
        study_id: study_id,
        session_id: session_id,
    });

    // stimuli = [{img: "../assets/tmp.jpg", filler: true, sim_x_result: 250, catch: false}]
    let n_trials = stimuli.length;

    const consent = {
        type: jsPsychExternalHtml,
        url: "consent.html",
        cont_btn: "start",
        execute_script: !_DEBUG,
    };
    timeline.push(consent);

    const instructions = {
        type: jsPsychConditionalInstructions,
        pages: [
            `<p>
      In this experiment, your task is to predict the path that a ball will take as it falls through an obstacle course.<br><br>
      The ball will start off suspended in mid-air.
      You will then be asked to indicate where you think the ball will hit the ground once it is let go, by clicking on positions where you think the ball will land.<br><br>
      You will receive points based on how accurate your predictions are - the closer your predictions are to the true path of the ball, the more points you receive.
      you may earn up to 10 points for each prediction you make, adding up to a total of 100 possible points on each scenario.<br>
      Therefore, on scenarios where you may not be sure of where the ball ends up, you may want to spread out your clicks to maximize the points you earn.
      `,
            `
      <p>
      <b>Note</b>: not all of the objects on the screen are solid. The <b>${background_colors[background_color_idx]}</b> objects on the screen are simply sections of the wall painted to look like objects. The ball will pass through these shapes as if it were not there, and will not bounce off of them.<br><br>

      Conversely, the <b>${background_colors[(background_color_idx + 1) % 2]}</b> shapes are solid objects, and the ball will bounce off of them.<br><br>

      On the next page, you will see an example of the kind of scene you will be asked to make predictions about.

      </p>`,
            `<p>
      This video shows an example of how the ball might fall through the obstacles.
      <b>Note that the ball fell right through the ${background_colors[background_color_idx]} objects.</b><br><br>

      On the next page, you will see how to make predictions about where the ball will land.
      </p>
      <video controls id="demo" src="assets/demo/demo1/world_${background_color_idx}.mp4"}></video>
      `,
            `<p>
      Here is an example of the prediction task that you will be asked to complete.<br><br>

      You will be asked to mark the spots you think that the ball will end up by clicking on the green area.
      You must click ten times to provide a range of places where you think the ball will land.
      These clicks will only register in the green area, and once you have indicated all ten places, you will see how the ball would actually fall.<br><br>

      If you are uncertain about where the ball will go, we would like you to reflect that in the spread of your predictions - for example, in the video below, it might be unclear whether the ball would bounce left or right at the beginning, and so half of the clicks were on the left side, and the other half were on the right side.
      On the other hand, if you want to indicate certainty about where the ball will land, you can click the same or similar positions multiple times, like how there are a few clicks right next to each other in the video.
      </p>

      <video id="demo" controls autoplay src='assets/demo/demo_${background_color_idx}.mp4'>
      </video>
      `,
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
        ],
        show_clickable_nav: true,
    };
    timeline.push(instructions);

    const comprehension = {
        type: jsPsychExternalHtml,
        url: () => {
            return ["comprehension_0.html", "comprehension_1.html"][background_color_idx];
        },
        cont_btn: "start",
        execute_script: !_DEBUG,
    };
    timeline.push(comprehension);

    let preload = {
        type: jsPsychPreload,
        auto_preload: true,
        images: stimuli.flatMap((elem) => {
            if (elem.filler) {
                return [elem["baseimg" + background_color_idx]];
            }
            return [elem["baseimg" + background_color_idx], elem.img0, elem.img1];
        }),
        video: stimuli.map((elem) => elem["recording" + background_color_idx]),
    };
    timeline.push(preload);

    let predictAndProbe = {
        timeline: [
            {
                type: jsPsychCanvasButtonResponse,
                stimulus: (c) => {
                    let ctx = c.getContext("2d");
                    let img = new Image();
                    img.src = jsPsych.timelineVariable("baseimg" + background_color_idx);
                    img.onload = () => {
                        ctx.drawImage(img, 0, 0);
                    };
                },
                choices: _DEBUG ? ["next"] : [],
                canvas_size: [602, 630],
                prompt: () => {
                    return `<p>
                Current points total: ${_STATE.cumulative_points}
                </p><p>
                Please click on the position that you think that the ball will end up at after dropping.
                <b>Remember: the ${background_colors[background_color_idx]} objects are not solid, and the ball will pass through them as if they were not there.</b>
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
                    let true_x = jsPsych.timelineVariable("sim_x_result");
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
                        // type: jsPsychHtmlButtonResponse,
                        type: jsPsychHtmlSliderResponse,
                        stimulus: () => {
                            let i = Math.round(Math.random());
                            _STATE.img = jsPsych.timelineVariable("img" + i);
                            _STATE.answer = 1 - i;
                            // console.log(1 - i);
                            return `
              <p>
              Pop quiz: below is the world that you just made predictions for, with two highlighted objects labeled (A) or (B).
              One of these objects is the original object in its original position, and the other is a copy of that object that has been shifted to a new position.
              <br><br>
              Which object is in the <b>correct, original</b> position?
              <br><br>
              Please select a choice using the slider below. The 'Next' button will become enabled after you have touched the slider.
              </p>
              <div id='img-wrapper' style='display:flex;flex-wrap:nowrap;padding-bottom:5vh;position:relative'>
              <div id='centerer' style='display:flex;margin:auto;position:relative'>
              <img src=${_STATE.img} style='width:100%'/>
              </div>
              </div>
              `;
                        },
                        on_finish: (data) => {
                            data.answer = _STATE.answer;
                            data.img = _STATE.img;
                        },
                        data: () => {
                            let tmp = targetStimuli[0];
                            let out = {};
                            for (let key in tmp) {
                                out[key] = jsPsych.timelineVariable(key);
                            }
                            out.type = "probe";
                            return out;
                        },
                        // choices: ["red", "blue"],
                        labels: [
                            "Sure that object (A) is in the original position",
                            "Not sure at all",
                            "Sure that object (B) is in the original position",
                        ],
                        require_movement: true,
                        css_classes: "slider-width",
                        // slider_width: 75,
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
                    let video = jsPsych.timelineVariable("recording" + background_color_idx);
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
                    button.style.visibility = "hidden";
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
                    window.location.replace("https://app.prolific.co/submissions/complete?cc=CT0HJL1O")
                }
            });
        },
    };
    timeline.push(debrief);

    jsPsych.run(timeline);
    console.log(jsPsych.data.get());
}

main().catch((err) => console.log(err));
