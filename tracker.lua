-- PSIV Tracker: Full Flag Sync (v11.3)
memory.usememorydomain("M68K BUS")

local event_flags_start = 0xFFF100 
local chest_flags_start = 0xFFF120 
local world_index_addr   = 0xFFF400 
local inventory_start    = 0xFFF410 

local data_filename = "data.txt"

local IDs = {
    amber = 0x8A, hydro = 0x98, digger = 0x97, sword = 0x77, 
    aero = 0x8F, alsh = 0x8D, torch = 0x8E, wand = 0x39,
    sapphire = 0x91, plate = 0x9A, vahal = 0x99, machine = 0x94, mantle = 0x3A,
    p_ring = 0x9B, m_ring = 0x9C, d_ring = 0x9D, r_ring = 0x9E, a_ring = 0x9F, mahlay = 0xA0
}

while true do
    local res = { amber=0, hydro=0, digger=0, sword=0, aero=0, alsh=0, torch=0, wand=0, 
                  sapphire=0, plate=0, vahal=0, machine=0, mantle=0, p_ring=0, m_ring=0, 
                  d_ring=0, r_ring=0, a_ring=0, mahlay=0 }
    
    for i = inventory_start, inventory_start + 39 do
        local val = memory.read_u8(i)
        for name, id in pairs(IDs) do
            if val == id then
                if name == "amber" then res.amber = res.amber + 1 else res[name] = 1 end
            end
        end
    end

    local q_flags = {}
    for i = 0, 100 do q_flags[i+1] = memory.read_u8(event_flags_start + i) end

    local c_flags = {}
    for i = 0, 31 do c_flags[i+1] = memory.read_u8(chest_flags_start + i) end

    local world = memory.read_u8(world_index_addr)

    local file = io.open(data_filename, "w")
    if file then
        local out = string.format("%d,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d", 
            world, 
            table.concat(q_flags, ","), 
            table.concat(c_flags, ","),
            res.amber, res.hydro, res.digger, res.sword, res.aero, res.alsh, res.torch, 
            res.wand, res.sapphire, res.plate, res.vahal, res.machine, res.mantle,
            res.p_ring, res.m_ring, res.d_ring, res.r_ring, res.a_ring, res.mahlay)
        file:write(out)
        file:close()
    end
    emu.frameadvance()
end
