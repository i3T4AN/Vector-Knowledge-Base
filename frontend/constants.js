/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         Application-wide constants
 * ======================================================================= */

/**
 * Constants used throughout the frontend to avoid magic strings.
 */
const CONSTANTS = {
    // Cluster filter values
    FILTER_ALL: "all",

    // Folder special values
    FOLDER_ROOT: "__root__",
    FOLDER_UNSORTED: "unsorted",
    FOLDER_NULL: "null"
};

// Make available globally
window.CONSTANTS = CONSTANTS;
