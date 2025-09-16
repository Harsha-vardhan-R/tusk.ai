
// Message from popup to background.
export interface Message {
    action : 'GET_STATE' | 'SET_STATE' | 'OPEN_LOG' | 'PROMPT' | 'SETTINGS';
    payload? : any;
};

// Response from background to popup.
export interface custResponse {
    success : boolean;
    payload? : any;
    error? : string;
};

// State of the extension for a particular tabID.
export interface State {
    prompt : string;
    button : string;
    output : string;
    // true if 
    generating : boolean;
}

