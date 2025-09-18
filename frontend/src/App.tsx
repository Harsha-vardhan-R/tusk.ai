import { useState, useEffect } from 'react';
import { Form, Label } from "radix-ui";
import type { custResponse, Message, State } from '../types.ts';

import './App.css'

function App() {
    const [buttonState, setButtonState] = useState('idle'); 
    const [promptState, setPromptState] = useState(''); 
    const [outputState, setOutputState] = useState(''); 
    const [tabIdConst, setTabId] = useState<number | null>(null);

    useEffect(() => {
        (async () => {
            const tabs = await browser.tabs.query({ active: true, currentWindow: true });
            if (tabs.length > 0 && tabs[0].id !== undefined) {
                setTabId(tabs[0].id);
            }
        })();
    }, []);

    useEffect(() => {
        if (tabIdConst === null || tabIdConst === undefined) return; // Wait until tabId is available

        (async () => {
            try {
                const raw = await browser.runtime.sendMessage({
                    action: "GET_STATE",
                    payload: { 
                        tabID : tabIdConst 
                    },
                });
                const state = raw as State;
                console.log("Successfully fetched state", state);

                setButtonState(state.button);
                setPromptState(state.prompt);
                setOutputState(state.output);
            } catch (error) {
                console.error("Failed to fetch state:", error);
            }
        })();
    }, [tabIdConst]);

    // Before the popup closes send the state back to 
    // background for saving.
    useEffect(() => {
        const handler = () => {
            browser.runtime.sendMessage({
                action: 'SET_STATE',
                payload: {
                    tabID: tabIdConst,
                    prompt: promptState,
                    button: buttonState,
                    output: outputState,
                },
            });
        };

        window.addEventListener('unload', handler);

        return () => {
            window.removeEventListener('unload', handler);
        };
    }, [promptState, buttonState, outputState, tabIdConst]);

    useEffect(() => {
        if (buttonState === 'generate')  { // prev state idle.
            browser.runtime.sendMessage({
                action: 'PROMPT',
                payload: {
                    tabID: tabIdConst,
                    prompt: promptState
                }
            }).then(
                response => {
                    if (response.success === true) {
                        setOutputState(response.output!);
                    } else {
                        setOutputState(response.error);
                    }
                    setButtonState('idle');
                }
            );
        }
    }, [buttonState]);


    const openLogsPage = () => {
        browser.runtime.sendMessage({action : 'OPEN_LOG'});
    }

    const PrmptButtonClicked = () => {
        if (buttonState === 'idle') {
            if (promptState === '') return;
            setButtonState('generate');
        } // will be reset when a response is sent from the backend.
    }

    return (
        <>
        <div>
        <div className="card">

        <Form.Root className="prompt">

        <Form.Field className="FormField" name="prompt">

        <Form.Control asChild>
        <textarea 
        className="Input" 
        placeholder="Ask Tusk..." 
        autoComplete="off"
        autoCorrect="off"
        spellCheck="false" 
        value={promptState}
        onChange={e => setPromptState(e.currentTarget.value)}
        required />
        </Form.Control>
        </Form.Field>

        <Form.Submit asChild>
        <button className="Button" onClick={PrmptButtonClicked}>
        {buttonState === 'idle' ? '🧠' : '❌'}
        </button>
        </Form.Submit>

        </Form.Root>

        <div className="output">
        <p>{outputState}</p>
        </div>

        <div className="titleBar">

        <Label.Root>
        <Label.Label className='lab'>tusk.ai</Label.Label>
        </Label.Root>
        <button className="but" title='Settings'> 🔧 </button>
        <button className="but" title='Logs' onClick={openLogsPage}> 📘 </button>
        <button className="but" title='Download Output'> ⬇️ </button>
        <button className="but" title='Copy Ouput'>

        <span style={{fontSize: '.875em', marginRight: '.125em', position: 'relative', top: '-.25em', left: '-.125em' }}>
        📄<span style={{ position: 'absolute', top: '.25em', left: '.25em' }} >📄</span>
        </span>
        </button>

        </div>

        </div>
        </div>
        </>
    )
}

export default App
