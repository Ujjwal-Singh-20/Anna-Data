import React, { use, useState } from 'react';
import axios from 'axios';
import { Analytics } from '@vercel/analytics/react';

const API_URL = "https://anna-data-452522242685.europe-west1.run.app";

function MockupSMS() {
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [responses, setResponses] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState(null);

  // scheduled run simulation
  const [scheduledRunResult, setScheduledRunResult] = useState(null);
  const [loadingScheduled, setLoadingScheduled] = useState(false);

  const handleSend = async (e) => {
    setLoadingMessages(true);
    e.preventDefault();
    setError(null);
    try {
      const res = await axios.post(`${API_URL}/mockup-webhook`, { phone, message });
      setResponses(prev => [
        ...prev,
        { phone, message, response: res.data }
      ]);
      setMessage('');
    } catch (err) {
      setError(err.message || 'Error sending message');
    }
    setLoadingMessages(false);
  };

  const handleSimulateScheduledRun = async () => {
    setLoadingScheduled(true);
    setScheduledRunResult(null);
    setError(null);
    try {
      const res = await axios.get(`${API_URL}/mockup-scheduled-run`);
      setScheduledRunResult(res.data);
    } catch (err) {
      setError(err.message || 'Error simulating scheduled run');
    }
    setLoadingScheduled(false);
  };

  function extractAdviceFromString(responseStr) {
    // This regex matches the 'advice': '...content...' or "advice": "...content..."
    const match = responseStr.match(/['"]advice['"]\s*:\s*(['"])([\s\S]*?)\1[,}]/);
    if (match && match[2]) {
      // replaced escaped newlines for pretty output
      return match[2].replace(/\\n/g, '\n');
    }
    return responseStr; // fallback to show the whole string
  }


  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-200 to-blue-300 flex flex-col items-center justify-center py-8">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl p-6">
        <h3 className="text-2xl font-bold text-center text-blue-500 mb-6">SMS Mockup Simulator for:</h3>
        <h2 className="text-4xl font-bold text-center text-blue-700 mb-6">Anna-Data</h2>
        <h5 className="text-xl font-bold text-center text-blue-600 mb-6">Annadata ke liye Anna-Data</h5>
        <form onSubmit={handleSend} className="space-y-4">
          <div>
            <label className="block text-gray-700 font-semibold mb-1" htmlFor="phone">Phone Number</label>
            <input
              id="phone"
              type="text"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="Enter phone number"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-gray-700 font-semibold mb-1" htmlFor="message">Message</label>
            <textarea
              id="message"
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Enter message"
              required
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {loadingMessages ? (
              <span className="flex items-center">
                <svg className="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                </svg>
                Processing...
              </span>
            ) : (
              "Send"
            )}
          </button>
        </form>

        {error && (
          <div className="mt-4 text-red-600 font-semibold bg-red-100 p-2 rounded">
            Error: {error}
          </div>
        )}

        <div className="mt-8">
          <h3 className="text-xl font-semibold mb-2 text-blue-700">Conversation</h3>
          <div className="bg-gray-100 rounded-lg p-4 h-64 overflow-y-auto flex flex-col space-y-4">
            {responses.length === 0 ? (
              <div className="text-gray-500 text-center">No messages yet.</div>
            ) : (
              responses.map((entry, idx) => (
                <div key={idx} className="flex flex-col space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="inline-block bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-bold">You</span>
                    <span className="text-sm text-gray-500">from {entry.phone}</span>
                  </div>
                  <div className="bg-blue-100 text-blue-900 rounded-xl px-4 py-2 self-start max-w-xs shadow">{entry.message}</div>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="inline-block bg-green-600 text-white px-3 py-1 rounded-full text-xs font-bold">Server</span>
                  </div>
                  <div className="bg-green-100 text-green-900 rounded-xl px-4 py-2 self-end max-w-xs shadow">
                    {/* {typeof entry.response === 'object'
                      ? JSON.stringify(entry.response.advice)
                      : String(entry.response)} */}
                      {extractAdviceFromString(entry.response.advice)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Simulate Scheduled Run Button */}
        <div className="mt-8 flex flex-col items-center">
          <button
            onClick={handleSimulateScheduledRun}
            className="bg-purple-600 text-white font-semibold py-2 px-6 rounded-lg hover:bg-purple-700 transition-colors mb-4"
            disabled={loadingScheduled}
          >
            {loadingScheduled ? (
              <span className="flex items-center">
                <svg className="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                </svg>
                Simulating...
              </span>
            ) : (
              "Simulate Scheduled Run"
            )}
          </button>

          {/* Show scheduled run result */}
          {scheduledRunResult && (
            <div className="w-full bg-gray-50 border border-gray-200 rounded-lg p-4 mt-2 shadow-inner">
              <h4 className="font-bold text-gray-700 mb-2">Scheduled Run Output</h4>
              <div className="text-sm text-gray-800">
                <div className="mb-1">
                  <span className="font-semibold">Processed Users:</span> {scheduledRunResult.processed_users}
                </div>
                <div className="font-semibold mb-1">Messages:</div>
                <ul className="list-disc list-inside space-y-2">
                  {scheduledRunResult.messages && scheduledRunResult.messages.length > 0 ? (
                    scheduledRunResult.messages.map((msg, idx) => (
                      <li key={idx} className="bg-white rounded p-2 shadow-sm">
                        <span className="text-blue-700 font-semibold">To:</span> {msg.to}<br />
                        <span className="text-gray-700">{msg.message}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-gray-500">No messages sent in this run.</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
      <footer className="mt-8 text-gray-400 text-xs text-center">
        &copy; 2025 SMS Mockup Demo - Powered by React & Tailwind CSS
      </footer>
      <Analytics/>
    </div>
  );
}

export default MockupSMS;
