import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../lib/api';

interface LogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LogoutModal({ isOpen, onClose }: LogoutModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[55] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-[#f6f4ee] border-2 border-[#1800ad] rounded-[32px] shadow-2xl p-6 md:p-8 max-w-sm w-full font-montserrat text-[#1800ad] flex flex-col gap-4 relative"
          >
            <h2 className="text-xl md:text-2xl font-black text-center uppercase tracking-wide">Logout</h2>
            <p className="text-sm text-[#1800ad]/80 font-bold text-center -mt-2">Are you sure you want to log out of Mootion?</p>
            
            <div className="flex gap-3 mt-2">
              <button
                type="button"
                onClick={onClose}
                className="w-1/2 py-3 bg-transparent border-2 border-[#1800ad] hover:bg-[#1800ad]/5 font-bold rounded-full text-center text-sm cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => api.logout()}
                className="w-1/2 py-3 bg-red-600 border-2 border-red-600 hover:bg-red-700 text-white font-bold rounded-full text-center text-sm cursor-pointer"
              >
                Logout
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
