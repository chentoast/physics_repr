const express = require("express");
const fs = require("fs");
const sqlite3 = require("sqlite3").verbose();
const asyncmutex = require("async-mutex");

const mutex = new asyncmutex.Mutex();

let app = express();

const exp = "exp_vgc2";

const datadb = new sqlite3.Database("participants.db");
_DEBUG = false;

function shuffle(array) {
    let currentIndex = array.length,
        randomIndex;

    // While there remain elements to shuffle.
    while (currentIndex != 0) {
        // Pick a remaining element.
        randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex--;

        // And swap it with the current element.
        [array[currentIndex], array[randomIndex]] = [array[randomIndex], array[currentIndex]];
    }

    return array;
}

app.use(express.static(__dirname + "/assets"));
app.use(express.static(__dirname + "/" + exp));
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: false }));

app.get("/", function (req, res) {
    res.sendFile(__dirname + "/" + exp + "/experiment.html");
});

app.get("/resetCounts", (req, res) => {
    stimdb
        .run("update worlds set count=0", (err) => {
            if (err) {
                console.log(err);
            }
        })
        .run("update stims set count=0", (err) => {
            if (err) {
                console.log(err);
            }
        });
});

async function sampleStimuli(db) {
    let sql = `
  select worlds.count as wcount,stims.count as scount,worlds.id as wid,stims.id as sid,
         worlds.world,worlds.*,stims.*
  from worlds
  inner join stims on
  worlds.world=stims.world
  where worlds.worldtype=? and stims.cond=?
  order by wcount,scount asc
  limit 1
  `;
    function getRowAndUpdate(worldType, cond) {
        return new Promise((resolve) => {
            db.get(sql, [worldType, cond], (err, row) => {
                if (err) {
                    console.log("an error happened when retrieving stimuli! ", err);
                    return;
                }
                // console.log(row)
                updateRowCount(row);
                resolve(row);
            });
        });
    }

    function updateRowCount(row) {
        db.serialize(() => {
            db.run("update worlds set count=? where id=?", [row.wcount + 1, row.wid], (err) => {
                if (err) {
                    console.log(err);
                    return;
                }
                console.log(`updated world ${row.world} with count ${row.wcount}`);
            }).run("update stims set count=? where id=?", [row.scount + 1, row.sid], (err) => {
                if (err) {
                    console.log(err);
                    return;
                }
                console.log(`updated stim ${row.modifiedImgBlue} with count ${row.scount}`);
            });
        });
    }

    let out = [];
    // let conds = ["col_early_rel", "col_early_irrel", "nocol_irrel"]
    // let conds = [
    //     "col_early_translate",
    //     "col_early_translate",
    //     "nocol_translate",
    //     "nocol_translate",
    // ];
    let conds = ["col_early_translate", "col_early_translate", "nocol_translate", "nocol_translate"];

    let maybeconds = shuffle(conds.concat(Array(4).fill("maybecol_translate")));
    let definiteconds = shuffle(conds.concat(Array(4).fill("col_late_translate")));
    // let maybeconds = shuffle(conds).concat("maybecol_rel", "maybecol_rel", "maybecol_irrel", "maybecol_irrel")
    // let definiteconds = shuffle(conds).concat("col_late_rel", "col_late_rel", "col_late_irrel", "col_late_irrel")

    for (let cond of maybeconds) {
        out.push(await getRowAndUpdate("maybe", cond));
    }
    for (let cond of definiteconds) {
        out.push(await getRowAndUpdate("definite", cond));
    }
    return out;
}

if ((exp === "exp1") | (exp === "exp_likelihood")) {
    const stimdb = new sqlite3.Database(exp + "/assets/stims.db");
    app.get("/sampleStimuli", async (req, res) => {
        let stimuli = await sampleStimuli(stimdb);
        res.json(stimuli);
    });
}

async function sampleStimuli_binary(exp_stimuli) {
    conds = {
        maybe: [
            "col_early_translate",
            "nocol_translate",
            "maybecol_translate",
        ],
        definite: [
            "col_early_translate",
            "nocol_translate",
            "col_late_translate",
        ],
    }
    const sampled_stimuli = [];

    shuffle(exp_stimuli);
    for (let stim of exp_stimuli) {
        // let counts = [stim.probe0_count, stim.probe1_count, stim.probe2_count];

        let cond_choices = conds[stim.worldtype]
        let cond_counts = cond_choices.map(c => {
            return Math.min(stim[`${c}_count0`], stim[`${c}_count1`])
        })
        // if there is more than 1 minimum, choose randomly among them
        let cond;
        if (cond_counts.filter(c => c === Math.min(...cond_counts)).length > 1) {
            let min_choices = cond_counts.map((c, i) => c === Math.min(...cond_counts) ? i : -1).filter(i => i != -1)
            cond = cond_choices[min_choices[Math.floor(Math.random() * min_choices.length)]]
        } else {
            cond = cond_choices[cond_counts.indexOf(Math.min(...cond_counts))]
        }

        // const shift = Math.random() < 0.5 ? 0 : 1;
        let shift_counts = [stim[`${cond}_count0`], stim[`${cond}_count1`]]
        let shift;
        if (shift_counts[0] == shift_counts[1]) {
            shift = Math.random() < 0.5 ? 0 : 1;
        } else {
            shift = shift_counts.indexOf(Math.min(...shift_counts))
        }
        console.log(cond, shift, stim[`${cond}_count0`], stim[`${cond}_count1`]);

        sampled_stimuli.push({
            world: stim.world,
            img: stim.img,
            recording: stim.recording,
            sim_x_result: stim.sim_x_result,
            cond: cond,
            filler: false,
            catch: false,
            baseImgRed: stim[`${cond}_baseImgRed`],
            baseImgBlue: stim[`${cond}_baseImgBlue`],
            modifiedImgRed: stim[`${cond}_modifiedImgRed${shift}`],
            modifiedImgBlue: stim[`${cond}_modifiedImgBlue${shift}`],
            obj_name: stim[`${cond}_object`],
            probe_shift_id: shift,
            worldType: stim.worldtype
        });
        stim[`${cond}_count${shift}`] += 1;
        console.log(sampled_stimuli.at(-1));
    }

    return sampled_stimuli;
}

if (exp === "exp1_binary") {
    let binary_stimuli = JSON.parse(fs.readFileSync(exp + "/assets/targets.json"));
    console.log(binary_stimuli);

    app.get("/sampleStimuli/binary", async (req, res) => {
        const release = await mutex.acquire();

        // bg_color = (Math.round(Math.random()) + 1).toString();
        let stims = await sampleStimuli_binary(binary_stimuli);
        console.log("sending stimuli", stims);
        res.json(stims);

        release();
    });
}

async function sampleStimuli_bg(
    backgroundStimuli,
    targetCount,
    conditions,
    conditionCount,
    bgConditionCount
) {
    const sampledStimuli = [];

    let nextConditionIndex = 0;

    let keys = Object.keys(backgroundStimuli);
    keys = shuffle(keys);

    let maybes = keys.filter((k) => backgroundStimuli[k].maybecol != undefined);
    let definites = keys.filter((k) => backgroundStimuli[k].col_late != undefined);

    function createStim(condition, world) {
        let bg_or_fg = Object.entries(bgConditionCount[condition]).sort((a, b) => a[1] - b[1])[0][0];
        console.log("background", bg_or_fg);

        let selectedStimulus = {
            baseimg0: backgroundStimuli[world][condition][bg_or_fg].baseimg0,
            baseimg1: backgroundStimuli[world][condition][bg_or_fg].baseimg1,
            recording0: backgroundStimuli[world][condition][bg_or_fg].recording0,
            recording1: backgroundStimuli[world][condition][bg_or_fg].recording1,
            obj_name: backgroundStimuli[world][condition][bg_or_fg].obj_name,
            worldtype: backgroundStimuli[world][condition][bg_or_fg].worldtype,
            sim_x_result: backgroundStimuli[world][condition][bg_or_fg].sim_x_result,
            obj_cond: condition,
            bg_cond: bg_or_fg,
        };
        let memory_stim = backgroundStimuli[world][condition].memory.stims.sort(
            (a, b) => a.count - b.count
        )[0];
        for (let [k, v] of Object.entries(memory_stim)) {
            selectedStimulus[k] = v;
        }

        conditionCount[condition] += 1;
        bgConditionCount[condition][bg_or_fg] += 1;
        memory_stim.count += 1;
        console.log(memory_stim.count);

        return selectedStimulus;
    }

    for (let i = 0; i < 4; i++) {
        let idx = Math.floor(Math.random() * maybes.length);
        let world = maybes.pop(idx);
        console.log(world);
        console.log("maybe");
        sampledStimuli.push(createStim("maybecol", world));

        idx = Math.floor(Math.random() * definites.length);
        world = definites.pop(idx);
        console.log(world);
        console.log("late");
        sampledStimuli.push(createStim("col_late", world));
    }

    let remainder = maybes.concat(definites);
    remainder = shuffle(remainder);
    for (i = 0; i < 4; i++) {
        let world = remainder.pop();
        console.log(world);
        console.log("early");
        sampledStimuli.push(createStim("col_early", world));

        world = remainder.pop();
        console.log(world);
        console.log("no");
        sampledStimuli.push(createStim("nocol", world));
    }

    return shuffle(sampledStimuli);
}

if (exp === "exp_background") {
    const conditions = ["maybecol", "col_late", "col_early", "nocol"];
    const conditionCount = { col_early: 0, col_late: 0, maybecol: 0, nocol: 0 };
    const bgConditionCount = conditions.reduce((acc, cond) => {
        acc[cond] = { background: 0, foreground: 0 };
        return acc;
    }, {});
    let backgroundStimuli = JSON.parse(fs.readFileSync(exp + "/assets/targets.json"));
    console.log(bgConditionCount);

    app.get("/sampleStimuli/bg", async (req, res) => {
        const release = await mutex.acquire();

        let targetCount = Object.values(conditionCount)[0] + 4;
        // bg_color = (Math.round(Math.random()) + 1).toString();
        let stims = await sampleStimuli_bg(
            backgroundStimuli,
            targetCount,
            conditions,
            conditionCount,
            bgConditionCount
        );
        res.json(stims);
        console.log(conditionCount);

        release();
    });
}

async function sampleStimuli_split(exp_stimuli) {
    const worldtype = Math.random() < 0.5 ? "1" : "2";
    const sampled_stimuli = [];

    shuffle(exp_stimuli);
    let exp_world_stimuli = exp_stimuli.filter((stim) => stim.worldtype === worldtype);
    for (let stim of exp_world_stimuli) {
        // const probe_obj = stim.probe1_count <= stim.probe2_count ? 1 : 2;

        let probe_obj = Math.random() < 0.5 ? 1 : 2;
        if (stim.probe1_count < stim.probe2_count) {
            probe_obj = 1;
        } else if (stim.probe1_count > stim.probe2_count) {
            probe_obj = 2;
        }
        const shift = Math.random() < 0.5 ? 1 : 2;

        sampled_stimuli.push({
            world: stim.world,
            worldtype: stim.worldtype,
            img: stim.background_img,
            recording: stim.recording,
            filler: false,
            probe_img0: stim[`probe${probe_obj}_${shift}_img0`],
            probe_img1: stim[`probe${probe_obj}_${shift}_img1`],
            probe_obj: probe_obj,
            probe_shift_id: shift,
            sim_x_result: stim.sim_x_result,
        });
        stim[`probe${probe_obj}_count`] += 1;
    }

    return sampled_stimuli;
}

if (exp.includes("split")) {
    let split_stimuli = JSON.parse(fs.readFileSync(exp + "/assets/targets.json"));
    console.log(split_stimuli);

    app.get("/sampleStimuli/split", async (req, res) => {
        const release = await mutex.acquire();

        // bg_color = (Math.round(Math.random()) + 1).toString();
        let stims = await sampleStimuli_split(split_stimuli);
        console.log("sending stimuli", stims);
        res.json(stims);

        release();
    });
}

async function sampleStimuli_bouncer(exp_stimuli) {
    const sampled_stimuli = [];

    shuffle(exp_stimuli);
    for (let stim of exp_stimuli) {
        // const probe_obj = stim.probe1_count <= stim.probe2_count ? 1 : 2;

        // let probe_obj = Math.random() < 0.5 ? 1 : 2;
        // if (stim.probe1_count < stim.probe2_count) {
        //     probe_obj = 1;
        // } else if (stim.probe1_count > stim.probe2_count) {
        //     probe_obj = 2;
        // }
        let probe_obj;
        let counts = [stim.probe0_count, stim.probe1_count, stim.probe2_count];
        if (counts[0] == counts[1] && counts[1] == counts[2]) {
            probe_obj = Math.floor(Math.random() * 3);
        } else if (counts[0] == counts[1]) {
            probe_obj = Math.random() < 0.5 ? 0 : 1;
        } else if (counts[1] == counts[2]) {
            probe_obj = Math.random() < 0.5 ? 1 : 2;
        } else if (counts[2] == counts[0]) {
            probe_obj = Math.random() < 0.5 ? 0 : 2;
        } else {
            probe_obj = counts.indexOf(Math.min(...counts));
        }
        console.log(probe_obj);
        const shift = Math.random() < 0.5 ? 1 : 2;

        sampled_stimuli.push({
            world: stim.world,
            img1: stim.img1,
            img2: stim.img2,
            recording1: stim.recording1,
            recording2: stim.recording2,
            sim_x_result1: stim.sim_x_result1,
            sim_x_result2: stim.sim_x_result2,
            filler: false,
            world1_probe_img0: stim[`world1_probe${probe_obj}_${shift}_img0`],
            world1_probe_img1: stim[`world1_probe${probe_obj}_${shift}_img1`],
            world2_probe_img0: stim[`world2_probe${probe_obj}_${shift}_img0`],
            world2_probe_img1: stim[`world2_probe${probe_obj}_${shift}_img1`],
            probe_obj: probe_obj,
            probe_shift_id: shift,
        });
        stim[`probe${probe_obj}_count`] += 1;
    }

    return sampled_stimuli;
}

if (exp.includes("bouncer")) {
    let bouncer_stimuli = JSON.parse(fs.readFileSync(exp + "/assets/targets.json"));
    console.log(bouncer_stimuli);

    app.get("/sampleStimuli/bouncer", async (req, res) => {
        const release = await mutex.acquire();

        let stims = await sampleStimuli_bouncer(bouncer_stimuli);
        console.log("sending stimuli", stims);
        res.json(stims);

        release();
    });
}

async function sampleStimuli_teleporter(exp_stimuli) {
    const sampled_stimuli = [];

    shuffle(exp_stimuli);
    for (let stim of exp_stimuli) {
        let counts = [stim.probe0_count, stim.probe1_count, stim.probe2_count];

        let probe_candidates = counts
            .map((c, i) => (c === Math.min(...counts) ? i : -1))
            .filter((i) => i != -1);
        let probe_idx = probe_candidates[Math.floor(Math.random() * probe_candidates.length)];
        let probe_obj = ["nocol", "teleport_consistent", "noteleport_consistent"][probe_idx];

        console.log(probe_obj);
        const shift = Math.random() < 0.5 ? 1 : 2;

        sampled_stimuli.push({
            world: stim.world,
            img1_1: stim.img1_1,
            img1_2: stim.img1_2,
            img2_1: stim.img2_1,
            img2_2: stim.img2_2,
            recording1_1: stim.recording1_1,
            recording1_2: stim.recording1_2,
            recording2_1: stim.recording2_1,
            recording2_2: stim.recording2_2,
            sim_x_result1: stim.sim_x_result1,
            sim_x_result2: stim.sim_x_result2,
            filler: false,
            color0_probe_img1: stim[`color0_${probe_obj}_shift${shift}_img1`],
            color1_probe_img0: stim[`color1_${probe_obj}_shift${shift}_img0`],
            color1_probe_img1: stim[`color1_${probe_obj}_shift${shift}_img1`],
            color0_probe_img0: stim[`color0_${probe_obj}_shift${shift}_img0`],
            probe_obj: probe_obj,
            probe_obj_idx: probe_idx,
            probe_shift_id: shift,
        });
        stim[`probe${probe_obj}_count`] += 1;
    }

    return sampled_stimuli;
}

if (exp.includes("teleporter")) {
    let teleporter_stimuli = JSON.parse(fs.readFileSync(exp + "/assets/targets.json"));
    // console.log(exp + "/assets/targets.json")
    console.log(teleporter_stimuli);

    app.get("/sampleStimuli/teleporter", async (req, res) => {
        const release = await mutex.acquire();

        let stims = await sampleStimuli_teleporter(teleporter_stimuli);
        console.log("sending stimuli", stims);
        res.json(stims);

        release();
    });
}

function sampleStimuliVGC(stimuli) {
    let out = [];
    for (let stim of stimuli) {
        let probeobj = "col1";
        if (stim.probes.length == 2) {
            probeobj = Math.random() < 0.5 ? "col1" : "col2";
        }

        let truecolor = Math.random() < 0.5 ? "blue" : "red";
        let distractorcolor = truecolor == "blue" ? "red" : "blue";
        let probe_num = Math.random() < 0.5 ? 0 : 1;
        out.push({
            img: stim.img,
            recording: stim.recording,
            world: stim.world,
            true_goal: stim.true_goal,
            filler: stim.filler,
            img_del: stim.img_del,
            recording_del: stim.recording_del,
            base_probe: stim[probeobj + "_base" + truecolor],
            distractor_probe: stim[probeobj + "_probe" + distractorcolor + probe_num],
            true_color: truecolor,
            answer: truecolor == "blue" ? 1 : 0,
            probetype: probeobj,
            probe_num: probe_num,
            object: stim[probeobj],
            worldtype: stim.worldtype,
        })
    }
    return out;
}

// if (exp === "exp_vgc") {
if (exp.startsWith("exp_vgc")) {
    console.log(exp + "/assets/targets/targets.json")
    const stimuli = JSON.parse(fs.readFileSync(exp + "/assets/targets/targets.json"));
    console.log(stimuli);

    app.get("/sampleStimuli/vgc", async (req, res) => {
        const release = await mutex.acquire();

        const sampledStimuli = sampleStimuliVGC(stimuli);
        console.log("sending stimuli", sampledStimuli);
        res.json(sampledStimuli);

        release();
    });
}

function saveData(db, data) {
    return new Promise((resolve) => {
        db.serialize(() => {
            db.run(`create table if not exists ${exp}(id integer primary key, data)`).run(
                `insert into ${exp}(data) values (?)`,
                [JSON.stringify(data)],
                (err) => {
                    if (err) {
                        console.log(`an error occurred while inserting data`);
                        console.log(err);
                        resolve(false);
                        return;
                    }
                    console.log(`successfully saved data`);
                    resolve(true);
                }
            );
        });
    });
}

app.post("/saveData", (req, res) => {
    console.log(req.body);
    if (_DEBUG) {
        return;
    }
    saveData(datadb, req.body).then((success) => {
        res.sendStatus(success ? 200 : 500);
    });
});

const port = 9999;
app.listen(port, () => {});
