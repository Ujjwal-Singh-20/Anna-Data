import React, { useState } from 'react';
import axios from 'axios';

function MockupSMS() {
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [responses, setResponses] = useState([]);
  const [error, setError] = useState(null);

  const handleSend = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await axios.post('/mockup-webhook', { phone, message });
      setResponses(prev => [
        ...prev,
        { phone, message, response: res.data }
      ]);
      setMessage('');
    } catch (err) {
      setError(err.message || 'Error sending message');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-200 flex flex-col items-center justify-center py-8">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6">
        <h2 className="text-3xl font-bold text-center text-blue-700 mb-6">SMS Mockup Simulator</h2>
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
            Send
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
                    <span className="text-sm text-gray-500">to {entry.phone}</span>
                  </div>
                  <div className="bg-blue-100 text-blue-900 rounded-xl px-4 py-2 self-start max-w-xs shadow">{entry.message}</div>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="inline-block bg-green-600 text-white px-3 py-1 rounded-full text-xs font-bold">Server</span>
                  </div>
                  <div className="bg-green-100 text-green-900 rounded-xl px-4 py-2 self-end max-w-xs shadow">
                    {typeof entry.response === 'object'
                      ? JSON.stringify(entry.response)
                      : String(entry.response)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      <footer className="mt-8 text-gray-400 text-xs text-center">
        &copy; {new Date().getFullYear()} SMS Mockup Demo &mdash; Powered by React & Tailwind CSS
      </footer>
    </div>
  );
}

export default MockupSMS;
