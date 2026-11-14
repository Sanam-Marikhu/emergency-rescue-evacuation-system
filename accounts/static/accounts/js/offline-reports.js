
const DB_NAME = "RescueConnectOfflineDB";
const DB_VERSION = 1;
const STORE_NAME = "pendingReports";

let isSyncing = false;

// Open the local database.
function openOfflineDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onupgradeneeded = (event) => {
            const database = event.target.result;

            if (!database.objectStoreNames.contains(STORE_NAME)) {
                database.createObjectStore(STORE_NAME, {
                    keyPath: "localId"
                });
            }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Save a report on this device.
async function saveOfflineReport(reportData) {
    const database = await openOfflineDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            STORE_NAME,
            "readwrite"
        );

        transaction.objectStore(STORE_NAME).add(reportData);

        transaction.oncomplete = () => {
            database.close();
            resolve();
        };

        transaction.onerror = () => {
            database.close();
            reject(transaction.error);
        };
    });
}

// Get all reports waiting to be synchronized.
async function getPendingReports() {
    const database = await openOfflineDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            STORE_NAME,
            "readonly"
        );

        const request = transaction
            .objectStore(STORE_NAME)
            .getAll();

        let reports = [];

        request.onsuccess = () => {
            reports = request.result;
        };

        transaction.oncomplete = () => {
            database.close();
            resolve(reports);
        };

        transaction.onerror = () => {
            database.close();
            reject(transaction.error);
        };
    });
}

// Delete a report only after the server confirms synchronization.
async function deleteOfflineReport(localId) {
    const database = await openOfflineDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            STORE_NAME,
            "readwrite"
        );

        transaction.objectStore(STORE_NAME).delete(localId);

        transaction.oncomplete = () => {
            database.close();
            resolve();
        };

        transaction.onerror = () => {
            database.close();
            reject(transaction.error);
        };
    });
}

// Synchronize pending reports with Django.
async function syncPendingReports(form, statusBox) {
    if (isSyncing || !navigator.onLine) {
        return;
    }

    isSyncing = true;

    try {
        const pendingReports = await getPendingReports();

        if (pendingReports.length === 0) {
            return;
        }

        const csrfToken = form.querySelector(
            'input[name="csrfmiddlewaretoken"]'
        )?.value;

        if (!csrfToken) {
            statusBox.hidden = false;
            statusBox.textContent =
                "Unable to synchronize: security token not found. " +
                "Reload this page and try again.";
            return;
        }

        statusBox.hidden = false;
        statusBox.textContent =
            `Synchronizing ${pendingReports.length} saved report(s)...`;

        let syncedCount = 0;

        for (const report of pendingReports) {
            try {
                const response = await fetch(
                    "/citizen/sync-offline-report/",
                    {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": csrfToken
                        },
                        body: JSON.stringify({
                            submission_id: report.localId,
                            data: report.data
                        })
                    }
                );

                const result = await response.json();

                if (!response.ok || !result.success) {
                    statusBox.textContent =
                        result.message ||
                        "A saved report could not be synchronized. " +
                        "It remains saved on this device.";
                    break;
                }

                await deleteOfflineReport(report.localId);
                syncedCount++;

            } catch (error) {
                console.error("Report synchronization failed:", error);

                statusBox.textContent =
                    "Connection interrupted. Your unsynchronized " +
                    "reports remain saved on this device.";
                break;
            }
        }

        const remainingReports = await getPendingReports();

        if (remainingReports.length === 0) {
            statusBox.textContent =
                syncedCount > 0
                    ? `${syncedCount} report(s) successfully synchronized.`
                    : "All saved reports are already synchronized.";
        } else if (syncedCount > 0) {
            statusBox.textContent =
                `${syncedCount} report(s) synchronized. ` +
                `${remainingReports.length} report(s) still waiting.`;
        }

    } catch (error) {
        console.error("Offline synchronization error:", error);

        statusBox.hidden = false;
        statusBox.textContent =
            "Could not synchronize reports. They remain saved locally.";

    } finally {
        isSyncing = false;
    }
}

// Handle offline saving and automatic synchronization.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("incident-report-form");
    const statusBox = document.getElementById("offline-status");

    if (!form || !statusBox) {
        return;
    }

    // Save reports locally when offline.
    form.addEventListener("submit", async (event) => {
        if (navigator.onLine) {
            return;
        }

        event.preventDefault();

        statusBox.hidden = false;
        statusBox.textContent = "Saving your report on this device...";

        const formData = new FormData(form);
        const reportData = {};

        formData.forEach((value, key) => {
            if (key !== "csrfmiddlewaretoken") {
                reportData[key] = value;
            }
        });

        form.querySelectorAll('input[type="checkbox"]').forEach(
            (checkbox) => {
                reportData[checkbox.name] =
                    checkbox.checked ? "true" : "false";
            }
        );

        const offlineReport = {
            localId: crypto.randomUUID(),
            data: reportData,
            savedAt: new Date().toISOString(),
            syncStatus: "pending"
        };

        try {
            await saveOfflineReport(offlineReport);

            statusBox.textContent =
                "Your report has been saved on this device. " +
                "It has NOT yet been submitted to the rescue system. " +
                "It will synchronize when internet returns.";

            form.reset();

        } catch (error) {
            console.error("Offline saving failed:", error);

            statusBox.textContent =
                "Could not save your report. Please try again.";
        }
    });

    // Try synchronization when this page loads.
    if (navigator.onLine) {
        syncPendingReports(form, statusBox);
    }

    // Automatically synchronize when internet returns.
    window.addEventListener("online", () => {
        syncPendingReports(form, statusBox);
    });
});
