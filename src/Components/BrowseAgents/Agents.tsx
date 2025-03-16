/* eslint-disable @typescript-eslint/no-unused-vars */
import { useState } from "react";
import InlineSVG from "react-inlinesvg";
import "./Agents.css";
import { FaSearch } from "react-icons/fa";
import { MdKeyboardArrowRight, MdKeyboardArrowDown } from "react-icons/md";

const agents = [
  {
    name: "Bitte Assistant",
    description:
      "General Bitte DEFI assistant, generate evm and near swaps and get market information",
    author: "bitte.near",
    verified: true,
    logo: "images/sonic-logo.png",
  },
  {
    name: "Bitte Assistant",
    description:
      "General Bitte DEFI assistant, generate evm and near swaps and get market information",
    author: "bitte.near",
    verified: true,
    logo: "images/sonic-logo.png",
  },
  {
    name: "Bitte Assistant",
    description:
      "General Bitte DEFI assistant, generate evm and near swaps and get market information",
    author: "bitte.near",
    verified: true,
    logo: "images/sonic-logo.png",
  },
  {
    name: "CoWSwap Assistant",
    description:
      "An assistant that generates EVM transaction data for CoW Protocol Interactions",
    author: "max-normal.near",
    verified: true,
    logo: "images/sonic-logo.png",
  },
  {
    name: "Meme.cooking",
    description:
      "It helps users create memecoins and retrieve memecoin information like daily stats and specific details",
    author: "rub3n.near",
    verified: true,
    logo: "images/sonic-logo.png",
  },
  {
    name: "CoinGecko Agent",
    description:
      "CoinGecko Agent is an AI helper with full access to CoinGecko's API. It provides real-time cryptocurrency data.",
    author: "markeljan.near",
    verified: true,
    category: "Investing",
    logo: "images/sonic-logo.png",
  },
];

const categories = ["Investing", "DAO", "Computational", "DeFi"];

const Agents = ({
  onToggle,
  onMobileNavToggle,
  isMobileNavVisible,
}: {
  onToggle: () => void;
  onMobileNavToggle: () => void;
  isMobileNavVisible: boolean;
}) => {
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

  const toggleCategory = (category: string) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((item) => item !== category)
        : [...prev, category]
    );
  };

  return (
    <div className="flex flex-col h-screen bg-black text-white overflow-hidden">
      {isMobileNavVisible && (
        <div
          className="fixed inset-0 bg-black bg-opacity-20 backdrop-blur-sm z-30 md:hidden"
          onClick={onMobileNavToggle}
        />
      )}
      <div
        className="bg-gray-900 p-4 flex items-center md:gap-5 gap-3 w-full"
        style={{ fontFamily: "orbitron" }}
      >
        <button
          onClick={() => {
            onToggle(); // Always toggle collapse state
            if (window.innerWidth < 768) {
              onMobileNavToggle(); // Only toggle mobile nav visibility on mobile screens
            }
          }}
          className="focus:outline-none"
        >
          <InlineSVG
            src="icons/Toggle.svg"
            className="w-5 h-5 cursor-pointer"
          />
        </button>
        <div className="text-lg text-gray-400 font-semibold">CHAT</div>
        <MdKeyboardArrowRight className="w-6 h-6" />
        <div className="text-white text-xs">VEJAS6QK0U1BTPQK</div>
      </div>

      {/* Layout with Sidebar & Main Content */}
      <div className="flex flex-col md:flex-row flex-grow h-screen">
        {/* Sidebar - Fixed, No Scroll */}
        <div className="md:w-1/4 w-full md:p-6 p-3">
          {/* Category Dropdown */}
          <div className="mt-6" style={{ fontFamily: "manrope" }}>
            <div
              className="flex items-center cursor-pointer"
              onClick={() => setIsCategoryOpen(!isCategoryOpen)}
            >
              <MdKeyboardArrowRight
                size={18}
                className={`mr-2 transition-transform ${
                  isCategoryOpen ? "rotate-90" : "rotate-0"
                }`}
              />
              <h3
                className="text-md font-semibold"
                style={{ fontFamily: "orbitron" }}
              >
                Category
              </h3>
            </div>

            {isCategoryOpen && (
              <div
                className="mt-2 flex flex-col gap-2"
                style={{ fontFamily: "manrope" }}
              >
                {categories.map((category) => (
                  <label
                    key={category}
                    className="flex items-center bg-gray-900 text-white px-4 py-3 rounded-lg cursor-pointer transition hover:bg-gray-800"
                  >
                    <input
                      type="checkbox"
                      className="hidden"
                      checked={selectedCategories.includes(category)}
                      onChange={() => toggleCategory(category)}
                    />
                    <span
                      className={`w-5 h-5 flex items-center justify-center border-2 border-white rounded ${
                        selectedCategories.includes(category)
                          ? "bg-black text-white"
                          : "bg-gray-700"
                      }`}
                    >
                      {selectedCategories.includes(category) && "✔"}
                    </span>
                    <span className="ml-2">{category}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content - Scrollable */}
        <div className="md:w-3/4 w-full p-6 overflow-y-auto h-screen">
          {/* Search Bar */}
          <div className="mb-6 flex justify-start relative">
            <FaSearch className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search"
              className="w-full md:w-1/2 p-3 pl-10 bg-transparent text-white border border-gray-500 rounded-lg"
              style={{ outline: "none", boxShadow: "none" }}
            />
          </div>

          {/* Agents Grid - Scrollable */}
          <div className="grid md:grid-cols-2 grid-cols-1 gap-6 mb-[100px]">
            {agents.map((agent, index) => (
              <div key={index} className="common cursor-pointer">
                <div
                  className="p-6 bg-gray-950 border-t border-l border-r border-gray-700 rounded-lg 
            hover:border-b hover:border-gray-500 
            transition-all duration-300 ease-in-out"
                >
                  {/* Logo, Title, and Button in the Same Line */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      {agent.logo && (
                        <img
                          src={agent.logo}
                          alt={`${agent.name} logo`}
                          className="h-8 w-8"
                        />
                      )}
                      <h5
                        className="text-base font-semibold"
                        style={{ fontFamily: "orbitron" }}
                      >
                        {agent.name.length > 10
                          ? `${agent.name.slice(0, 10)}...`
                          : agent.name}
                      </h5>
                    </div>
                    <button
                      className="py-2 px-3 bg-gray-700 hover:bg-gray-600 cursor-pointer rounded text-sm"
                      style={{ fontFamily: "manrope" }}
                    >
                      Run Agent
                    </button>
                  </div>

                  {/* Description */}
                  <p
                    className="text-sm text-gray-400 truncate"
                    style={{
                      fontFamily: "manrope",
                      maxWidth: "calc(100% - 1rem)",
                    }}
                  >
                    {agent.description.length > 45
                      ? `${agent.description.slice(0, 45)}...`
                      : agent.description}
                  </p>

                  {/* Author and Verification */}
                  <div className="mt-4 flex items-center justify-between">
                    {/* Author Section */}
                    <div
                      className="flex items-center gap-2"
                      style={{ fontFamily: "manrope" }}
                    >
                      <span className="text-gray-500 text-sm">By</span>
                      <img
                        src="https://pbs.twimg.com/profile_images/1804597854725431296/fLn9-v6H_400x400.jpg"
                        alt="Author Logo"
                        className="w-5 h-5 rounded-full"
                      />
                      <span className="text-gray-500 text-sm">
                        {agent.author}
                      </span>
                    </div>

                    {/* Verified Badge */}
                    {agent.verified && (
                      <span
                        className="px-3 flex flex-row items-center justify-center gap-1 py-1 text-xs text-green-500 border border-green-500 rounded-2xl"
                        style={{ fontFamily: "manrope" }}
                      >
                        <InlineSVG
                          src="icons/green-tick.svg"
                          className="w-3 h-3"
                        />{" "}
                        Verified
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Agents;
