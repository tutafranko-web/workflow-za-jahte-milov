/**
 * Google Apps Script — Charter Job Outreach Autopilot
 *
 * Sends all matching Gmail drafts with couple_cv.pdf attached, every few hours.
 * Combined with Claude routine that drafts new applications daily, this gives
 * full autonomy: drafts appear in Gmail → script attaches CV + sends → repeat.
 *
 * ONE-TIME SETUP (5 min):
 *  1. Upload `couple_cv.pdf` (from c:\Users\WWW\Desktop\ai\claude code\job-outreach\data\)
 *     to your Google Drive. Anywhere. Note the file ID:
 *     Right-click → "Share" → "Copy link" → ID is between /d/ and /view in URL.
 *  2. Go to https://script.google.com → "New project" → name it "Charter Outreach".
 *  3. Paste this entire file into the editor (replacing the default code).
 *  4. Replace CV_DRIVE_FILE_ID below with the file ID from step 1.
 *  5. (Optional) Adjust SUBJECT_FILTER if you want a different filter.
 *  6. Click Save (💾).
 *  7. Click Run dropdown → select `setupDailyTrigger` → Run.
 *     Browser asks for Gmail + Drive permission → click Allow.
 *  8. DONE. The script will now check every 4 hours for new drafts and send them.
 *
 * WHAT EACH FUNCTION DOES:
 *  - `sendAllDrafts()` — attaches CV to every draft matching filter, sends them,
 *    deletes the draft. Runs every 4h once trigger is set up.
 *  - `setupDailyTrigger()` — creates the recurring trigger. Run ONCE.
 *  - `removeAllTriggers()` — kills the recurring trigger. Run if you want to stop.
 *  - `listMatchingDrafts()` — dry-run: just lists drafts that would be sent.
 *  - `testSendOneDraft()` — sends ONLY the first matching draft. Use to test setup.
 */

const CV_DRIVE_FILE_ID = '1yTZoFrQYVCfgfYo2Y8WSDrkWMdToyhCl';
const SUBJECT_FILTER = 'Captain + Stewardess couple';
const REPLY_TO = 'tutafranko@gmail.com';
const TRIGGER_HOURS = 4; // re-scan drafts every 4 hours
const MAX_SENDS_PER_RUN = 20; // safety cap

function sendAllDrafts() {
  if (CV_DRIVE_FILE_ID === 'REPLACE_WITH_COUPLE_CV_FILE_ID') {
    throw new Error('Set CV_DRIVE_FILE_ID at the top of the script before running.');
  }

  let cv;
  try {
    cv = DriveApp.getFileById(CV_DRIVE_FILE_ID).getBlob();
  } catch (e) {
    Logger.log(`ERROR: cannot fetch CV file ${CV_DRIVE_FILE_ID}: ${e}`);
    return;
  }

  const drafts = GmailApp.getDrafts();
  let sent = 0;
  let skipped = 0;
  let errors = 0;

  for (const draft of drafts) {
    if (sent >= MAX_SENDS_PER_RUN) {
      Logger.log(`Reached MAX_SENDS_PER_RUN (${MAX_SENDS_PER_RUN}), stopping.`);
      break;
    }

    const msg = draft.getMessage();
    const subject = msg.getSubject() || '';

    if (SUBJECT_FILTER && !subject.includes(SUBJECT_FILTER)) {
      skipped++;
      continue;
    }

    const to = msg.getTo();
    const body = msg.getPlainBody();
    if (!to || !body) {
      Logger.log(`SKIP empty draft id=${draft.getId()}`);
      skipped++;
      continue;
    }

    try {
      GmailApp.sendEmail(to, subject, body, {
        attachments: [cv],
        replyTo: REPLY_TO,
        name: 'Franko Tuta',
      });
      draft.deleteDraft();
      Logger.log(`SENT  ${to}  |  ${subject}`);
      sent++;
      Utilities.sleep(3000); // 3-sec pause to spread Gmail send rate
    } catch (e) {
      Logger.log(`ERROR  ${to}  |  ${e}`);
      errors++;
    }
  }

  Logger.log(`\nDONE. sent=${sent}, skipped=${skipped}, errors=${errors}`);
}

function setupDailyTrigger() {
  // Remove any existing triggers first
  removeAllTriggers();

  // Create new time-based trigger that runs every TRIGGER_HOURS hours
  ScriptApp.newTrigger('sendAllDrafts')
    .timeBased()
    .everyHours(TRIGGER_HOURS)
    .create();

  Logger.log(`Trigger created. sendAllDrafts will run every ${TRIGGER_HOURS} hours.`);
  Logger.log('Running it once now to send any existing drafts...');
  sendAllDrafts();
}

function removeAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  for (const t of triggers) {
    if (t.getHandlerFunction() === 'sendAllDrafts') {
      ScriptApp.deleteTrigger(t);
      Logger.log(`Removed trigger id=${t.getUniqueId()}`);
    }
  }
}

function listMatchingDrafts() {
  const drafts = GmailApp.getDrafts();
  let n = 0;
  for (const draft of drafts) {
    const msg = draft.getMessage();
    const subject = msg.getSubject() || '';
    if (!SUBJECT_FILTER || subject.includes(SUBJECT_FILTER)) {
      Logger.log(`${msg.getTo()}  |  ${subject}`);
      n++;
    }
  }
  Logger.log(`\n${n} drafts match filter "${SUBJECT_FILTER}"`);
}

function testSendOneDraft() {
  const drafts = GmailApp.getDrafts();
  for (const draft of drafts) {
    const msg = draft.getMessage();
    const subject = msg.getSubject() || '';
    if (!SUBJECT_FILTER || subject.includes(SUBJECT_FILTER)) {
      const to = msg.getTo();
      const body = msg.getPlainBody();
      const cv = DriveApp.getFileById(CV_DRIVE_FILE_ID).getBlob();
      GmailApp.sendEmail(to, subject, body, {
        attachments: [cv],
        replyTo: REPLY_TO,
        name: 'Franko Tuta',
      });
      draft.deleteDraft();
      Logger.log(`TEST SENT: ${to} | ${subject}`);
      return;
    }
  }
  Logger.log('No matching drafts found.');
}
