import React, { useEffect, useState } from 'react';
import './App.css';

const API_BASE = import.meta.env.VITE_API_URL || "";

function App() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [hidePaid, setHidePaid] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/scan_invoices`, { credentials: 'include' })
      .then(res => {
        if (res.status === 401) {
          // Automatically redirect to OAuth flow
          setLoading(false);
          setRedirecting(true);
          window.location.href = `${API_BASE}/authorize`;
          return null;
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
      })
      .then(data => {
        if (data) { // Only process if we have data (not null from 401 case)
          setInvoices(data);
        }
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching invoices:', error);
        // Check if this might be an authentication issue
        if (error.message.includes('401') || error.message.includes('not_authenticated')) {
          setLoading(false);
          setRedirecting(true);
          window.location.href = `${API_BASE}/authorize`;
        } else {
          setLoading(false);
        }
      });
  }, []);

  const markAsPaid = (id) => {
    fetch(`${API_BASE}/mark_paid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ id }),
    })
      .then(res => res.json())
      .then(() => {
        setInvoices(invoices =>
          invoices.map(inv =>
            inv.id === id ? { ...inv, paid: true } : inv
          )
        );
      })
      .catch(error => console.error('Error marking as paid:', error));
  };

  const markAsUnpaid = (id) => {
    fetch(`${API_BASE}/mark_unpaid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ id }),
    })
      .then(res => res.json())
      .then(() => {
        setInvoices(invoices =>
          invoices.map(inv =>
            inv.id === id ? { ...inv, paid: false } : inv
          )
        );
      })
      .catch(error => console.error('Error marking as unpaid:', error));
  };

  if (loading || redirecting) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-neutral-600 text-lg">
            {redirecting ? "Redirecting to login..." : "Loading invoices..."}
          </p>
        </div>
      </div>
    );
  }

  if (invoices.length === 0) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-md mx-auto bg-white rounded-2xl shadow-soft p-8 text-center">
            <div className="w-16 h-16 bg-neutral-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-neutral-800 mb-2">No invoices found</h2>
            <p className="text-neutral-600">Check your email connection and try again.</p>
          </div>
        </div>
      </div>
    );
  }

  const totalAmount = invoices.reduce((sum, inv) => sum + inv.amount, 0);
  const totalDeposit = invoices.reduce((sum, inv) => sum + inv.deposit_required, 0);
  const totalGovernmentContribution = invoices.reduce((sum, inv) => sum + (inv.amount - inv.deposit_required), 0);
  const unpaidInvoices = invoices.filter(inv => !inv.paid);
  const paidInvoices = invoices.filter(inv => inv.paid);

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-neutral-200">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-neutral-900">Nursery Invoices</h1>
              <p className="text-neutral-600 mt-1">Track your childcare payments and deposits</p>
            </div>
            <div className="text-right">
              <div className="text-sm text-neutral-500">Total this period</div>
              <div className="text-2xl font-bold text-primary-700">£{totalAmount.toFixed(2)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-soft p-6">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-neutral-600">Total Invoices</p>
                <p className="text-2xl font-bold text-neutral-900">{invoices.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-soft p-6">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-neutral-600">Government Contribution</p>
                <p className="text-2xl font-bold text-neutral-900">£{totalGovernmentContribution.toFixed(2)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-soft p-6">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-neutral-600">Paid Invoices</p>
                <p className="text-2xl font-bold text-neutral-900">{paidInvoices.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="bg-white rounded-xl shadow-soft p-6 mb-6">
          <label className="flex items-center cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                checked={hidePaid}
                onChange={e => setHidePaid(e.target.checked)}
                className="sr-only"
              />
              <div className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                hidePaid ? 'bg-primary-600' : 'bg-neutral-300'
              }`}>
                <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ${
                  hidePaid ? 'translate-x-5' : 'translate-x-0.5'
                } mt-0.5`}></div>
              </div>
            </div>
            <span className="ml-3 text-sm font-medium text-neutral-700">Hide paid invoices</span>
          </label>
        </div>

        {/* Invoice List */}
        <div className="space-y-4">
          {invoices
            .filter(inv => !hidePaid || !inv.paid)
            .map((inv, i) => (
              <div key={inv.id || i} className="bg-white rounded-xl shadow-soft overflow-hidden">
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center mb-2">
                        <div className="text-sm font-medium text-neutral-500 bg-neutral-100 px-2 py-1 rounded-lg">
                          {inv.date}
                        </div>
                        {inv.paid && (
                          <button
                            onClick={() => markAsUnpaid(inv.id)}
                            className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 transition-colors duration-200 cursor-pointer"
                            title="Click to mark as unpaid"
                          >
                            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                            Paid
                          </button>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <p className="text-sm font-medium text-neutral-600">Invoice Amount</p>
                          <p className="text-xl font-bold text-neutral-900">£{inv.amount.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-neutral-600">Deposit Required</p>
                          <p className="text-xl font-bold text-primary-700">£{inv.deposit_required.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-neutral-600">Government Contribution</p>
                          <p className="text-xl font-bold text-green-600">£{(inv.amount - inv.deposit_required).toFixed(2)}</p>
                        </div>
                      </div>
                    </div>

                    {!inv.paid && (
                      <button
                        className="ml-6 px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                        onClick={() => markAsPaid(inv.id)}
                      >
                        Mark as Paid
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

export default App;
